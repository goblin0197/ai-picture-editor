# 应用全局配置：集中从仓库根目录的 .env 读取所有可调项。
# 约定：字段名小写，对应大写、无前缀的环境变量（如 IMAGE_PROVIDER → image_provider）。
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 仓库根目录：本文件在 backend/app/config.py，向上三层（app→backend→根）即仓库根。
# .env 与 frontend/dist 都以此为基准定位，保证无论从哪个工作目录启动都能找到。
ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """全部配置项的集中定义。取值优先级：环境变量 > .env 文件 > 此处默认值。

    只声明带默认值的字段，这样缺省环境下也能直接启动（对开发友好）。
    """

    # env_file 指向仓库根 .env；extra="ignore" 表示 .env 里多余的键不报错，只取已声明字段。
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "development"  # 运行环境标识，production 时启用静态托管等生产行为
    api_port: int = 7302  # 后端 API 端口（非默认值，避免与本机其他项目冲突）

    # 本机共享 PostgreSQL 实例，用其惯例默认管理员；5433 是因为默认的 5432 已被其他项目占用
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/retouch"
    # 本机共享 Redis 实例；db 0/1 已被其他项目占用，本项目固定用 db 2
    redis_url: str = "redis://localhost:6379/2"

    # 本机共享 MinIO 实例，使用其默认端口与默认根账号
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "retouch"
    # 签名 URL 有效期，秒
    s3_url_ttl: int = 900

    # HS256 要求密钥不短于 32 字节
    jwt_secret: str = "dev-only-secret-please-change-in-production"
    jwt_ttl_hours: int = 24  # 会话令牌有效期（小时）

    # 图像提供方开关：mock（默认，占位图、不花钱）| dashscope（真实模型）|
    # openai（本仓库本地扩展，接本机 OpenAI 兼容网关）。切换即改整条生成链路走哪个后端。
    # image provider: mock | dashscope
    image_provider: str = "mock"
    dashscope_api_key: str = ""
    # 业务空间专属域名为 https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com
    dashscope_base_url: str = "https://dashscope.aliyuncs.com"
    text_to_image_model: str = "qwen-image-3.0-pro"
    image_edit_model: str = "qwen-image-edit-max"
    planner_model: str = "qwen-plus"

    # @property：把方法伪装成只读属性，调用处写 settings.is_production（不加括号）。
    @property
    def is_production(self) -> bool:
        """是否生产环境。main.py 据此决定是否由后端托管前端静态产物。"""
        return self.app_env == "production"

    # @property：同上，前端构建产物目录以属性形式暴露，随取随算而非固定存储。
    @property
    def frontend_dist(self) -> Path:
        """前端构建产物 frontend/dist 的绝对路径（生产环境静态托管的根目录）。"""
        return ROOT_DIR / "frontend" / "dist"


# @lru_cache：无参函数首次调用时构造 Settings，之后返回同一实例（进程内单例）。
# 好处是全项目共享一份配置、只解析一次 .env；代价是测试改环境变量后需 get_settings.cache_clear()。
@lru_cache
def get_settings() -> Settings:
    """获取全局唯一的配置实例。所有模块都应经此函数取配置，不要各自新建 Settings()。"""
    return Settings()
