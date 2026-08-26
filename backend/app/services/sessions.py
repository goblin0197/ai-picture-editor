"""编辑会话业务逻辑：建会话、图片墙挂载、改名、切当前图与历史维护。"""

import uuid  # 各 id 参数的类型
from collections.abc import Iterable  # 挂载素材时的可迭代入参

from sqlalchemy import delete, func, select  # 删除语句、聚合函数（max）、查询
from sqlalchemy.ext.asyncio import AsyncSession  # 异步会话类型

from app.layers import document_of  # 以素材为底图生成画布文档
from app.models import Asset, EditHistory, EditSession, SessionAsset  # 相关 ORM 模型
from app.models.edit_history import HISTORY_LIMIT  # 历史上限，超出即删旧行

TITLE_LIMIT = 80  # 会话标题最大长度（与 EditSession.title 列宽一致）
DEFAULT_TITLE = "未命名会话"  # 空标题时的兜底文案


class SessionNotFound(Exception):
    # 会话不存在或不属于该用户。路由层据此返回 404（不区分两种情况，避免泄露）。
    pass


def normalize_title(text: str | None) -> str:
    """标题归一：压缩所有空白为单个空格、截断到 80 字，空串回退默认标题。"""
    cleaned = " ".join((text or "").split())
    return cleaned[:TITLE_LIMIT] or DEFAULT_TITLE


async def _next_position(session: AsyncSession, session_id: uuid.UUID) -> int:
    """取图片墙下一个位置序号（当前最大值 + 1；空墙从 1 开始）。"""
    last = await session.scalar(
        select(func.max(SessionAsset.position)).where(SessionAsset.session_id == session_id)
    )
    return (last or 0) + 1


async def _attach(session: AsyncSession, record: EditSession, assets: Iterable[Asset]) -> None:
    """把素材挂上图片墙：跳过已在墙上的（复合主键天然去重），其余按顺序追加。"""
    # 先查当前已在墙上的素材 id，避免撞复合主键
    known = set(
        await session.scalars(
            select(SessionAsset.asset_id).where(SessionAsset.session_id == record.id)
        )
    )
    position = await _next_position(session, record.id)

    for asset in assets:
        if asset.id in known:
            continue
        session.add(SessionAsset(session_id=record.id, asset_id=asset.id, position=position))
        known.add(asset.id)
        position += 1


async def _append_history(
    session: AsyncSession, record: EditSession, action: str, params: dict, result: dict
) -> None:
    """追加一条历史：seq 取会话内最大值 + 1，并删除超出 HISTORY_LIMIT 的旧行。"""
    last = await session.scalar(
        select(func.max(EditHistory.seq)).where(EditHistory.session_id == record.id)
    )
    seq = (last or 0) + 1
    session.add(
        EditHistory(
            user_id=record.user_id,
            session_id=record.id,
            seq=seq,
            action=action,
            params=params,
            result=result,
        )
    )
    # 滚动窗口：只留最近 HISTORY_LIMIT 条（seq <= 本次序号 - 上限的都删）
    await session.execute(
        delete(EditHistory).where(
            EditHistory.session_id == record.id, EditHistory.seq <= seq - HISTORY_LIMIT
        )
    )


async def create(
    session: AsyncSession,
    user_id: uuid.UUID,
    current: Asset,
    wall: Iterable[Asset] = (),
    title: str | None = None,
) -> EditSession:
    """新建会话。current 进入画布，wall 中其余图片仅进图片墙备选。"""
    record = EditSession(
        user_id=user_id,
        title=normalize_title(title),
        original_asset_id=current.id,  # 源头素材 = 首张进入画布的图
        current_asset_id=current.id,
        # 文档以底图起点建立（Pydantic 模型 → dict，mode="json" 保证 UUID 等可 JSON 化）
        document=document_of(current).model_dump(mode="json"),
    )
    session.add(record)
    # flush 拿到数据库生成的 record.id，后续挂图片墙/写历史都要用
    await session.flush()

    await _attach(session, record, [current, *wall])
    await _append_history(session, record, "create_session", {}, {"asset_id": str(current.id)})
    await session.commit()
    await session.refresh(record)
    return record


async def load(session: AsyncSession, session_id: uuid.UUID) -> EditSession:
    """不带用户过滤的读取，仅供已确认归属的后台任务使用。"""
    record = await session.get(EditSession, session_id)
    if record is None:
        raise SessionNotFound
    return record


async def get_for_user(
    session: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID
) -> EditSession:
    """主键 + user_id 联合条件查询：别人的会话与不存在的会话一律 SessionNotFound（→404）。"""
    record = await session.scalar(
        select(EditSession).where(EditSession.id == session_id, EditSession.user_id == user_id)
    )
    if record is None:
        raise SessionNotFound
    return record


async def list_for_user(
    session: AsyncSession, user_id: uuid.UUID, limit: int = 50
) -> list[EditSession]:
    """该用户的会话列表，按最后更新时间倒序（最近编辑的排最上）。"""
    result = await session.scalars(
        select(EditSession)
        .where(EditSession.user_id == user_id)
        .order_by(EditSession.updated_at.desc())
        .limit(limit)
    )
    return list(result)


async def assets_of(session: AsyncSession, record: EditSession) -> list[Asset]:
    """图片墙的全部素材，按挂载时的 position 排序（顺序稳定）。"""
    result = await session.scalars(
        select(Asset)
        .join(SessionAsset, SessionAsset.asset_id == Asset.id)
        .where(SessionAsset.session_id == record.id)
        .order_by(SessionAsset.position)
    )
    return list(result)


async def history_of(session: AsyncSession, record: EditSession) -> list[EditHistory]:
    """编辑历史，seq 倒序（最新一步在最前）。"""
    result = await session.scalars(
        select(EditHistory)
        .where(EditHistory.session_id == record.id)
        .order_by(EditHistory.seq.desc())
    )
    return list(result)


async def record_result(
    session: AsyncSession,
    record: EditSession,
    assets: Iterable[Asset],
    action: str,
    params: dict,
    result: dict,
) -> None:
    """工具产出并入图片墙并留下编辑记录。不改当前图，采用与否交给用户。"""
    await _attach(session, record, assets)
    await _append_history(session, record, action, params, result)
    await session.commit()


async def rename(session: AsyncSession, record: EditSession, title: str) -> EditSession:
    """改标题。归一逻辑同创建时；不写历史（改名不属于画布操作）。"""
    record.title = normalize_title(title)
    await session.commit()
    await session.refresh(record)
    return record


async def switch_current(session: AsyncSession, record: EditSession, asset: Asset) -> EditSession:
    """切换画布当前图。修订号递增，使旧修订号上的选区与遮罩失效。"""
    if record.current_asset_id != asset.id:
        record.current_asset_id = asset.id
        record.revision += 1
        # 画布重置为新图的底图文档：切图是「换一张重画」，不保留旧图层
        record.document = document_of(asset).model_dump(mode="json")
        await _attach(session, record, [asset])  # 确保新图也在图片墙上
        await _append_history(
            session,
            record,
            "switch_current",
            {"asset_id": str(asset.id)},
            {"revision": record.revision},
        )
    # 切的就是当前图时静默返回，不递增修订号、不留历史
    await session.commit()
    await session.refresh(record)
    return record
