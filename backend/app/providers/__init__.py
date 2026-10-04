# 图像提供方的“工厂 + 登记表”：对外暴露 get_image_provider()，按配置返回对应实现。
# 新增一个平台的完整流程只有两步：在 providers/ 下写一个遵守 ImageProvider 协议的类，
# 再到本文件的 if 分支里登记一行——调用方（generation.execute）永远只认协议，无需改动。
from functools import lru_cache

from app.config import get_settings
from app.providers.base import GenerateRequest, ImageProvider, ProviderError
from app.providers.mock import MockImageProvider


# @lru_cache：无参调用，令整个进程共享同一个 provider 单例（含其复用的 httpx 客户端），
# 避免每次生成都重建连接池。配置在运行期不变，缓存住结果是安全的。
@lru_cache
def get_image_provider() -> ImageProvider:
    """按配置选择实现。新增平台只需在此登记，调用方无需改动。"""
    name = get_settings().image_provider  # 读取 IMAGE_PROVIDER 配置值

    # 逐个匹配已登记的 provider 名。mock 在文件顶部 import（默认实现、零外部依赖）。
    if name == "mock":
        return MockImageProvider()
    # dashscope/openai 延迟到分支内 import：没启用时就不去加载其依赖、触发缺配置报错。
    if name == "dashscope":
        from app.providers.dashscope import DashScopeImageProvider

        return DashScopeImageProvider()
    if name == "openai":
        from app.providers.openai_images import OpenAIImagesProvider

        return OpenAIImagesProvider()

    # 配了未知名字：明确报错，而不是静默退回某个默认，免得用错模型还不自知。
    raise ProviderError(f"未知的 IMAGE_PROVIDER：{name}")


# 模块公开接口：调用方从 app.providers 直接导入这些名字，无需深入子模块。
__all__ = ["GenerateRequest", "ImageProvider", "ProviderError", "get_image_provider"]
