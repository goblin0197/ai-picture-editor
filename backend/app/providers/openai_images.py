"""OpenAI 兼容的图像生成接口（`/v1/images/generations`）。

与 `dashscope.py` 的差别：一次 POST 同步返回结果，不需要提交任务再轮询状态；
尺寸参数是 `WIDTHxHEIGHT`（用 x 分隔），而不是百炼的 `WIDTH*HEIGHT`。

响应里的 `url` 指向网关侧的外部存储，仍须立即下载转存到自有存储
（见 `services/generation.py`），不要把外部链接直接存进 `result`。

复用 `dashscope_*` 配置项：本机网关即 OpenAI 兼容形态，两个协议共用同一套
地址与密钥，没必要再增加一组语义重复的配置。
"""

import asyncio  # 信号量限流、并发补足与并发下载
import base64  # 解码响应里的内联 b64_json 图片

import httpx  # 异步 HTTP 客户端

from app.config import get_settings
from app.providers.base import GenerateRequest, ImageProvider, ProgressCallback, ProviderError

# base_url 已含 `/v1`，这里不要再带，否则会拼成 `/v1/v1/...`
_IMAGES_PATH = "/images/generations"

# 网关对并发敏感：实测 2 路并发稳定、同时压 3 路以上会返回
# `Upstream service temporarily unavailable`，故限制同时进行的请求数。
_MAX_CONCURRENCY = 2

_SUBMIT_PROGRESS = (15, "提交生成请求")  # 提交阶段的 (进度, 文案)
_DOWNLOAD_PROGRESS = (70, "下载生成结果")  # 下载阶段的 (进度, 文案)


# 遵守 ImageProvider 协议的本地扩展适配器，对应 IMAGE_PROVIDER=openai。
# 复用 dashscope_* 那套配置项（地址/密钥），因为本机网关就是 OpenAI 兼容形态。
class OpenAIImagesProvider(ImageProvider):
    """OpenAI Images API 兼容实现。"""

    name = "openai"  # provider 标识，与配置值 IMAGE_PROVIDER=openai 对应

    # 构造函数：校验密钥、建长连客户端，并初始化一把限流信号量。
    def __init__(self) -> None:
        settings = get_settings()
        # 复用 dashscope 的密钥字段：网关同一套鉴权，没必要再加一组语义重复的配置。
        if not settings.dashscope_api_key:
            raise ProviderError("未配置 DASHSCOPE_API_KEY")
        self._model = settings.text_to_image_model
        self._client = httpx.AsyncClient(
            base_url=settings.dashscope_base_url,
            headers={"Authorization": f"Bearer {settings.dashscope_api_key}"},
            # 单张实测约 35 秒，批量与排队留出余量
            timeout=180.0,
        )
        # 信号量把同时在途的请求数压到 _MAX_CONCURRENCY，避免触发网关的并发上限（502）。
        self._gate = asyncio.Semaphore(_MAX_CONCURRENCY)

    # 生成入口：与 dashscope 不同，这里是“一次 POST 同步拿结果”，没有轮询阶段。
    # 流程：拒参考图 → 报提交进度 → 收集结果项 → 报下载进度 → 并发取字节。
    async def generate(
        self, request: GenerateRequest, on_progress: ProgressCallback | None = None
    ) -> list[bytes]:
        if request.references:
            # OpenAI 图片接口不接受参考图（编辑能力走 /v1/images/edits，尚未接入）
            raise ProviderError("当前提供方不支持参考图")

        if on_progress:
            await on_progress(*_SUBMIT_PROGRESS)

        items = await self._collect(request, on_progress)  # 拿到 data[] 里的结果项（url/b64）

        if on_progress:
            await on_progress(*_DOWNLOAD_PROGRESS)
        # 每个结果项各自取字节（内联直接解码、否则下载），并发完成。
        return await asyncio.gather(*(self._one(item) for item in items))

    # 私有：想办法凑够 request.count 张结果项，兼容各网关对 n 的不同脾气。详见下方 docstring。
    async def _collect(
        self, request: GenerateRequest, on_progress: ProgressCallback | None
    ) -> list[dict]:
        """凑够 request.count 张，但不强求——拿到几张算几张。

        不同 OpenAI 兼容网关对 `n` 的支持不一致，且拒绝方式不同：
        `gpt-image-2` 收下 `n` 却只回 1 张，`agnes-image-*` 直接报 `n must be 1`。
        所以先按 count 试一次，拿到不足（无论是少给还是报错）就回到单张模式补足。

        补足阶段按 `_MAX_CONCURRENCY` 分批：并发过高会被网关拒绝，而串行会把
        耗时乘上张数。单张失败不放弃整批——真实模型按张计费，已经生成的图不该
        因为同批某一张被拒就全部丢弃；只有一张都没拿到才算失败。
        """
        items: list[dict] = []
        # 第一次尝试：只有要多张时才试 n=count，单张没必要走这轮。
        if request.count > 1:
            try:
                items = self._parse(await self._post(request, request.count))
            except ProviderError:
                # 该模型不接受 n>1，退回单张模式即可，不是真正的失败
                items = []

        # 一次就凑够了（网关真给了多张、或本就只要 1 张）：截断到 count 直接返回。
        if len(items) >= request.count:
            return items[: request.count]

        if on_progress:
            await on_progress(40, f"该模型不支持一次多张，正在逐张生成（已有 {len(items)} 张）")

        failed = 0  # 累计失败张数，仅用于最后给用户一个提示
        pending = request.count - len(items)  # 还差几张
        while pending > 0:
            before = len(items)  # 记下本轮开始前的张数，用于判断本轮是否有进展
            batch = min(pending, _MAX_CONCURRENCY)  # 本轮并发张数，别超过限流上限
            # 并发发 batch 个单张请求；return_exceptions=True 让个别失败不炸掉整组 gather。
            results = await asyncio.gather(
                *(self._post(request, 1) for _ in range(batch)),
                return_exceptions=True,
            )
            for result in results:
                # 请求本身抛异常（网络/超时等）：计一次失败，继续看下一个。
                if isinstance(result, BaseException):
                    failed += 1
                    continue
                try:
                    items.extend(self._parse(result))  # 解析成功则并入结果项
                except ProviderError:
                    failed += 1  # 响应虽回但解析失败（如报错体），同样计失败
            # 一轮下来一张都没新增（全部失败或响应为空），再重试也是白费
            if len(items) == before:
                break
            pending = request.count - len(items)  # 更新还差多少，进入下一轮

        # 一张都没拿到才算整批失败；否则哪怕只有部分成功也照常返回（按张计费，不浪费）。
        if not items:
            raise ProviderError("生成失败：网关未返回任何图片")

        # 有失败但仍拿到部分：告知用户实际交付张数，别让人以为漏了。
        if failed and on_progress:
            await on_progress(
                60, f"有 {failed} 张未能生成，返回已完成的 {len(items)} 张"
            )
        return items[: request.count]

    # 私有：发一次图片生成 POST。用 async with self._gate 占一个信号量名额，
    # 从而把并发压在 _MAX_CONCURRENCY 以内——所有出网请求都必须经由这里。
    async def _post(self, request: GenerateRequest, count: int) -> httpx.Response:
        async with self._gate:
            return await self._client.post(_IMAGES_PATH, json=self._payload(request, count))

    # 私有：组装 OpenAI Images 接口的请求体。入参 count 由调用方决定（首轮=count，补足=1）。
    def _payload(self, request: GenerateRequest, count: int) -> dict:
        payload: dict = {
            "model": self._model,
            "prompt": request.prompt,
            "n": count,
            "size": f"{request.width}x{request.height}",  # 尺寸用 x 分隔（dashscope 用 *）
        }
        # 下面两项不在 OpenAI 规范内，但网关实测会原样接收
        if request.negative_prompt:
            payload["negative_prompt"] = request.negative_prompt
        if request.seed is not None:
            payload["seed"] = request.seed
        return payload

    # 私有：把单个结果项还原成图片字节。入参 item 为 data[] 里的一项。
    async def _one(self, item: dict) -> bytes:
        """各网关返回形式不一：优先用内联 base64，否则下载 url。"""
        if item.get("b64_json"):
            return base64.b64decode(item["b64_json"])  # 内联形式：直接 base64 解码，无需再联网

        url = item.get("url")
        if not url:
            raise ProviderError("生成结果缺少图片数据")  # 两种形式都没有，判失败

        # url 形式：另起临时客户端下载（同 dashscope，链接指向外部存储、不带本适配器鉴权头）。
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(url)
        if response.status_code != httpx.codes.OK:
            raise ProviderError("生成结果下载失败")
        return response.content

    # @staticmethod：只依赖传入的 response、不碰实例状态，故声明为静态方法。
    # 私有：解析响应、做错误校验，成功时返回 data[] 结果项列表。
    @staticmethod
    def _parse(response: httpx.Response) -> list[dict]:
        try:
            body = response.json()
        except ValueError as exc:
            # 非 JSON 多半是网关层错误页（如 502），转成统一异常上抛。
            raise ProviderError(
                f"模型服务返回非 JSON 响应（HTTP {response.status_code}）"
            ) from exc

        # 非 200：尽量从 OpenAI 风格的 error.message 里取原因，取不到就报 HTTP 状态。
        if response.status_code != httpx.codes.OK:
            error = body.get("error") if isinstance(body, dict) else None
            message = error.get("message") if isinstance(error, dict) else None
            raise ProviderError(message or f"模型服务错误 HTTP {response.status_code}")

        data = body.get("data") or []
        if not data:
            raise ProviderError("模型服务未返回图片")  # 200 但空 data，按失败处理
        return data
