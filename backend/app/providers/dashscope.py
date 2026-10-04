# 百炼（DashScope）千问图像模型适配器，对应 IMAGE_PROVIDER=dashscope（真实模型、会计费）。
# 与 mock 的根本差别：走“异步提交 + 轮询”两段式——先 POST 提交任务拿 task_id，再定时 GET
# 查任务状态，直到成功/失败；成功后拿到的图片链接 24 小时过期，须立即下载转存到自有存储。
import asyncio  # 轮询间隔的 sleep、以及多张结果的并发下载
import base64  # 参考图内联时做 base64 编码

import httpx  # 异步 HTTP 客户端

from app.config import get_settings
from app.providers.base import (
    GenerateRequest,
    ImageProvider,
    ProgressCallback,
    ProviderError,
)

_SUBMIT_PATH = "/api/v1/services/aigc/image-generation/generation"  # 提交任务的接口路径
_TASK_PATH = "/api/v1/tasks/{task_id}"  # 按 task_id 查询任务状态的接口路径

_POLL_INTERVAL = 3.0  # 两次轮询之间的间隔（秒）
_POLL_TIMEOUT = 300.0  # 轮询总超时（秒），超过即判超时失败，避免无限等待
# 任务终态集合：轮询到其中任一状态即停止。注意 UNKNOWN 也算终态（当作异常收尾）。
_TERMINAL = {"SUCCEEDED", "FAILED", "CANCELED", "UNKNOWN"}

# 非终态到 (进度, 阶段文案) 的映射：轮询时据此上报中间进度，让前端进度条动起来。
_PROGRESS = {"PENDING": (10, "排队中"), "RUNNING": (45, "生成中")}


# 遵守 ImageProvider 协议的百炼适配器。构造时校验密钥、建长连客户端。
class DashScopeImageProvider(ImageProvider):
    """百炼千问图像模型。

    使用异步接口：提交任务取回 task_id 后轮询。部分账号不开放同步调用，
    异步路径同时能提供真实的排队与执行状态。
    """

    name = "dashscope"  # provider 标识，与配置值 IMAGE_PROVIDER=dashscope 对应

    # 构造函数：读取配置、校验密钥、初始化可复用的 httpx 异步客户端。
    def __init__(self) -> None:
        settings = get_settings()
        # 没配密钥直接判失败，避免带着空 Authorization 头去请求、白白拿一堆 401。
        if not settings.dashscope_api_key:
            raise ProviderError("未配置 DASHSCOPE_API_KEY")
        self._model = settings.text_to_image_model  # 文生图模型名（如 qwen-image-3.0-pro）
        # 复用同一个客户端：base_url 与鉴权头预置好，后续提交/轮询都走它。
        self._client = httpx.AsyncClient(
            base_url=settings.dashscope_base_url,
            headers={"Authorization": f"Bearer {settings.dashscope_api_key}"},
            timeout=30.0,  # 单次 HTTP 请求超时；生成总时长由 _POLL_TIMEOUT 控制
        )

    # 生成入口：串起“提交→轮询→下载”三步，返回全部候选图字节。
    # 入参：request 生成请求；on_progress 可选进度回调。出参：图片字节列表。
    async def generate(
        self, request: GenerateRequest, on_progress: ProgressCallback | None = None
    ) -> list[bytes]:
        task_id = await self._submit(request)  # 第一步：提交任务，拿到 task_id
        urls = await self._await_result(task_id, on_progress)  # 第二步：轮询至成功，取回链接
        # 第三步：并发下载全部结果链接（链接 24h 过期，由上层转存自有存储）。
        return await asyncio.gather(*(self._download(url) for url in urls))

    # 私有：把 GenerateRequest 组装成百炼提交接口要的 JSON 结构。
    # 入参：request 生成请求。出参：请求体字典（含 model/input/parameters）。
    def _payload(self, request: GenerateRequest) -> dict:
        # 本地对象存储无法被模型服务访问，参考图一律以 base64 内联
        # （data URI 把图片直接塞进请求体，省去让外部服务回来拉本地 URL 的不可行路径）。
        content: list[dict] = [
            {"image": f"data:image/png;base64,{base64.b64encode(raw).decode()}"}
            for raw in request.references
        ]
        content.append({"text": request.prompt})  # 参考图之后再追加文本提示词

        parameters: dict = {
            "n": request.count,  # 期望生成张数
            "size": f"{request.width}*{request.height}",  # 百炼尺寸用 * 分隔（openai 用 x）
            "watermark": False,  # 关闭水印
        }
        # 反向提示词/种子仅在给了值时才带上，避免传空值干扰模型默认行为。
        if request.negative_prompt:
            parameters["negative_prompt"] = request.negative_prompt
        if request.seed is not None:
            parameters["seed"] = request.seed

        # 百炼把提示词与参考图放进 input.messages（多模态对话形态），生成参数单列 parameters。
        return {
            "model": self._model,
            "input": {"messages": [{"role": "user", "content": content}]},
            "parameters": parameters,
        }

    # 私有：提交生成任务。出参：task_id 字符串，供后续轮询用。
    async def _submit(self, request: GenerateRequest) -> str:
        response = await self._client.post(
            _SUBMIT_PATH,
            json=self._payload(request),
            # 关键头：声明异步模式，服务端才会返回 task_id 而不是同步等出图。
            headers={"X-DashScope-Async": "enable"},
        )
        body = self._parse(response)  # 统一校验 HTTP 与业务错误，非 JSON/报错都会抛
        task_id = body.get("output", {}).get("task_id")
        if not task_id:
            raise ProviderError("模型服务未返回任务 ID")  # 拿不到 task_id 无法轮询，直接失败
        return task_id

    # 私有：轮询任务直到终态。入参：task_id；on_progress 进度回调。出参：结果图片链接列表。
    async def _await_result(self, task_id: str, on_progress: ProgressCallback | None) -> list[str]:
        # 用事件循环时钟算出截止时刻，循环里每轮与它比较，超时即放弃。
        deadline = asyncio.get_running_loop().time() + _POLL_TIMEOUT

        while True:
            response = await self._client.get(_TASK_PATH.format(task_id=task_id))
            output = self._parse(response).get("output", {})
            status = output.get("task_status", "UNKNOWN")  # 缺字段时按 UNKNOWN（终态）处理

            if status in _TERMINAL:
                # 到终态：非成功一律抛错（含 FAILED/CANCELED/UNKNOWN），把服务端消息带出。
                if status != "SUCCEEDED":
                    raise ProviderError(f"生成任务{status}：{output.get('message', '未知原因')}")
                return _extract_urls(output)  # 成功：从结构里提取图片链接返回

            # 非终态：把 PENDING/RUNNING 映射成进度上报，让前端看到“排队中/生成中”。
            if on_progress and status in _PROGRESS:
                await on_progress(*_PROGRESS[status])

            # 每轮结束先查是否超时、再睡一个间隔——避免刚好卡在超时点还白等一轮。
            if asyncio.get_running_loop().time() > deadline:
                raise ProviderError("生成任务超时")
            await asyncio.sleep(_POLL_INTERVAL)

    # 私有：下载单张结果图，返回原始字节。
    # 另起临时客户端而非复用 self._client：结果链接指向对象存储域名、与 base_url 无关，
    # 且不该带上百炼的 Authorization 头。
    async def _download(self, url: str) -> bytes:
        """结果 URL 有效期 24 小时，须立即取回并转存到自有存储。"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
        if response.status_code != httpx.codes.OK:
            raise ProviderError("生成结果下载失败")
        return response.content

    # @staticmethod：不依赖实例状态，纯粹解析响应，故声明为静态方法。
    # 私有：把 HTTP 响应统一解析成字典，顺带做错误校验（提交与轮询都用它）。
    @staticmethod
    def _parse(response: httpx.Response) -> dict:
        try:
            body = response.json()
        except ValueError as exc:
            # 非 JSON 多半是网关/代理层出错（如 502 HTML 页），转成统一异常。
            raise ProviderError(f"模型服务返回非 JSON 响应（HTTP {response.status_code}）") from exc

        # 两种失败都要拦：HTTP 非 200，或返回体里带 code 字段（百炼用它表业务错误）。
        if response.status_code != httpx.codes.OK or "code" in body:
            raise ProviderError(body.get("message") or f"模型服务错误 HTTP {response.status_code}")
        return body


# 私有模块级函数：从成功任务的 output 里把图片链接抽出来。
# 结构是 choices[].message.content[] 里带 image 字段的项——展平后收集所有 image 链接。
def _extract_urls(output: dict) -> list[str]:
    urls = [
        item["image"]
        for choice in output.get("choices", [])
        for item in choice.get("message", {}).get("content", [])
        if "image" in item
    ]
    if not urls:
        raise ProviderError("生成任务成功但未返回图片")  # 状态成功却没图，视为异常
    return urls
