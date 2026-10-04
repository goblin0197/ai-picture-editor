# 素材业务逻辑：图片校验、写入对象存储、落库，以及按 user_id 隔离的查询。
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import storage
from app.models import Asset
from app.models.asset import AssetKind, AssetSource
from app.services.images import ImageMeta, probe


# 私有：拼对象存储 key，以 users/<user_id>/ 为前缀天然隔离不同用户的对象。
# 即便有人猜到 key 规律，也因签名 URL 与查询层的 user_id 联合过滤而无法越权访问。
def _storage_key(user_id: uuid.UUID, asset_id: uuid.UUID, extension: str) -> str:
    return f"users/{user_id}/{asset_id}.{extension}"


# 校验图片→写对象存储→落库，返回 Asset。上传与生成两条链路都复用它。
# 入参：session 会话；user_id 归属；data 图片字节；kind/source 素材种类与来源；
#       meta 可选的预校验结果（上传路由已 probe 过就直接传入，省一次解码）。
async def create_from_bytes(
    session: AsyncSession,
    user_id: uuid.UUID,
    data: bytes,
    kind: AssetKind,
    source: AssetSource,
    meta: ImageMeta | None = None,
) -> Asset:
    """校验图片、写入对象存储并落库。所有素材以 user_id 为前缀隔离。"""
    # 未传入 meta 时在此 probe 校验；已校验过则复用，避免重复解码。
    meta = meta or probe(data)
    asset_id = uuid.uuid4()
    # key 里带上 user_id 前缀与解码得到的真实扩展名。
    key = _storage_key(user_id, asset_id, meta.extension)

    # 先写对象存储，再写库；下面各字段全部取自 probe 的解码结果而非客户端上报。
    await storage.put(key, data, meta.content_type)

    asset = Asset(
        id=asset_id,
        user_id=user_id,
        kind=kind,
        source=source,
        storage_key=key,
        image_format=meta.image_format,
        width=meta.width,
        height=meta.height,
        size_bytes=meta.size_bytes,
        has_alpha=meta.has_alpha,
    )
    session.add(asset)
    await session.commit()
    return asset


# 列出某用户的素材，按创建时间倒序、限量返回，天然按 user_id 过滤不会串到他人素材。
# 入参：user_id 归属；limit 上限。出参：Asset 列表。
async def list_for_user(session: AsyncSession, user_id: uuid.UUID, limit: int = 50) -> list[Asset]:
    result = await session.scalars(
        select(Asset).where(Asset.user_id == user_id).order_by(Asset.created_at.desc()).limit(limit)
    )
    return list(result)


# 按 id 取单个素材，出参 Asset 或 None。是全项目「防越权」的核心查询。
# 入参：user_id 归属；asset_id 主键。
async def get_for_user(
    session: AsyncSession, user_id: uuid.UUID, asset_id: uuid.UUID
) -> Asset | None:
    """按主键与 user_id 联合查询，避免越权访问他人素材。"""
    # where 同时约束主键与 user_id：别人的素材查出来就是 None，路由层据此回 404 而非 403，
    # 这样不会因状态码差异泄露「该资源是否存在」。
    return await session.scalar(select(Asset).where(Asset.id == asset_id, Asset.user_id == user_id))
