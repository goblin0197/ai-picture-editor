"""OpenAI 兼容的图像生成接口（`/v1/images/generations`）。

与 `dashscope.py` 的差别：一次 POST 同步返回结果，不需要提交任务再轮询状态；
尺寸参数是 `WIDTHxHEIGHT`（用 x 分隔），而不是百炼的 `WIDTH*HEIGHT`。

响应里的 `url` 指向网关侧的外部存储，仍须立即下载转存到自有存储
（见 `services/generation.py`），不要把外部链接直接存进 `result`。

复用 `dashscope_*` 配置项：本机网关即 OpenAI 兼容形态，两个协议共用同一套
地址与密钥，没必要再增加一组语义重复的配置。
"""

import asyncio
import base64

import httpx

from app.config import get_settings
from app.providers.base import GenerateRequest, ImageProvider, ProgressCallback, ProviderError

# base_url 已含 `/v1`，这里不要再带，否则会拼成 `/v1/v1/...`
_IMAGES_PATH = "/images/generations"

# 网关对并发敏感：实测 2 路并发稳定、同时压 3 路以上会返回
# `Upstream service temporarily unavailable`，故限制同时进行的请求数。
_MAX_CONCURRENCY = 2

_SUBMIT_PROGRESS = (15, "提交生成请求")
_DOWNLOAD_PROGRESS = (70, "下载生成结果")


class OpenAIImagesProvider(ImageProvider):
    """OpenAI Images API 兼容实现。"""

    name = "openai"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.dashscope_api_key:
            raise ProviderError("未配置 DASHSCOPE_API_KEY")
        self._model = settings.text_to_image_model
        self._client = httpx.AsyncClient(
            base_url=settings.dashscope_base_url,
            headers={"Authorization": f"Bearer {settings.dashscope_api_key}"},
            # 单张实测约 35 秒，批量与排队留出余量
            timeout=180.0,
        )
        self._gate = asyncio.Semaphore(_MAX_CONCURRENCY)

    async def generate(
        self, request: GenerateRequest, on_progress: ProgressCallback | None = None
    ) -> list[bytes]:
        if request.references:
            # OpenAI 图片接口不接受参考图（编辑能力走 /v1/images/edits，尚未接入）
            raise ProviderError("当前提供方不支持参考图")

        if on_progress:
            await on_progress(*_SUBMIT_PROGRESS)

        items = await self._collect(request, on_progress)

        if on_progress:
            await on_progress(*_DOWNLOAD_PROGRESS)
        return await asyncio.gather(*(self._one(item) for item in items))

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
        if request.count > 1:
            try:
                items = self._parse(await self._post(request, request.count))
            except ProviderError:
                # 该模型不接受 n>1，退回单张模式即可，不是真正的失败
                items = []

        if len(items) >= request.count:
            return items[: request.count]

        if on_progress:
            await on_progress(40, f"该模型不支持一次多张，正在逐张生成（已有 {len(items)} 张）")

        failed = 0
        pending = request.count - len(items)
        while pending > 0:
            before = len(items)
            batch = min(pending, _MAX_CONCURRENCY)
            results = await asyncio.gather(
                *(self._post(request, 1) for _ in range(batch)),
                return_exceptions=True,
            )
            for result in results:
                if isinstance(result, BaseException):
                    failed += 1
                    continue
                try:
                    items.extend(self._parse(result))
                except ProviderError:
                    failed += 1
            # 一轮下来一张都没新增（全部失败或响应为空），再重试也是白费
            if len(items) == before:
                break
            pending = request.count - len(items)

        if not items:
            raise ProviderError("生成失败：网关未返回任何图片")

        if failed and on_progress:
            await on_progress(
                60, f"有 {failed} 张未能生成，返回已完成的 {len(items)} 张"
            )
        return items[: request.count]

    async def _post(self, request: GenerateRequest, count: int) -> httpx.Response:
        async with self._gate:
            return await self._client.post(_IMAGES_PATH, json=self._payload(request, count))

    def _payload(self, request: GenerateRequest, count: int) -> dict:
        payload: dict = {
            "model": self._model,
            "prompt": request.prompt,
            "n": count,
            "size": f"{request.width}x{request.height}",
        }
        # 下面两项不在 OpenAI 规范内，但网关实测会原样接收
        if request.negative_prompt:
            payload["negative_prompt"] = request.negative_prompt
        if request.seed is not None:
            payload["seed"] = request.seed
        return payload

    async def _one(self, item: dict) -> bytes:
        """各网关返回形式不一：优先用内联 base64，否则下载 url。"""
        if item.get("b64_json"):
            return base64.b64decode(item["b64_json"])

        url = item.get("url")
        if not url:
            raise ProviderError("生成结果缺少图片数据")

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(url)
        if response.status_code != httpx.codes.OK:
            raise ProviderError("生成结果下载失败")
        return response.content

    @staticmethod
    def _parse(response: httpx.Response) -> list[dict]:
        try:
            body = response.json()
        except ValueError as exc:
            raise ProviderError(
                f"模型服务返回非 JSON 响应（HTTP {response.status_code}）"
            ) from exc

        if response.status_code != httpx.codes.OK:
            error = body.get("error") if isinstance(body, dict) else None
            message = error.get("message") if isinstance(error, dict) else None
            raise ProviderError(message or f"模型服务错误 HTTP {response.status_code}")

        data = body.get("data") or []
        if not data:
            raise ProviderError("模型服务未返回图片")
        return data
