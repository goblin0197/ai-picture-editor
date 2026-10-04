# 素材出参的 Pydantic 模型：把 Asset ORM 对象转成带签名 URL 的响应体
import uuid  # id 字段的 UUID 类型
from datetime import datetime  # created_at 字段的时间类型

from pydantic import BaseModel  # Pydantic 模型基类

from app import storage  # 对象存储封装，用于生成签名 URL
from app.models import Asset  # 素材 ORM 模型（构造入参类型）
from app.models.asset import AssetKind, AssetSource  # 素材类别/来源枚举


# 出参模型：对外描述一张素材；不含 storage_key（内部 key 不外泄）
class AssetOut(BaseModel):
    id: uuid.UUID  # 素材主键
    kind: AssetKind  # 素材类别（原图/生成图/主体等）
    source: AssetSource  # 素材来源（上传/生成/工具）
    image_format: str  # 实际图片格式，如 png/jpeg
    width: int  # 宽（像素）
    height: int  # 高（像素）
    size_bytes: int  # 文件字节数
    has_alpha: bool  # 是否含透明通道
    created_at: datetime  # 创建时间
    url: str  # 可直接访问的签名 URL（而非内部 storage_key）

    # @classmethod：工厂方法，从 ORM 对象构造出参；cls 为 AssetOut 类
    @classmethod
    def of(cls, asset: Asset) -> "AssetOut":
        # 逐字段拷贝 ORM 值；返回类型注解写成字符串是为前向引用（类尚未定义完）
        return cls(
            id=asset.id,
            kind=asset.kind,
            source=asset.source,
            image_format=asset.image_format,
            width=asset.width,
            height=asset.height,
            size_bytes=asset.size_bytes,
            has_alpha=asset.has_alpha,
            created_at=asset.created_at,
            # 每次都用 storage_key 重新签发 URL：签名有时效，实时生成才不会过期
            url=storage.signed_url(asset.storage_key),
        )
