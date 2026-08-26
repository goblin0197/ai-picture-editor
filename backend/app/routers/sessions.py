"""编辑会话路由：/api/sessions 的增删查改、历史查询与对话指令。

所有接口都需要登录（CurrentUser），跨用户访问一律 404（见 _load）。
"""

import uuid  # 路径参数与素材 id 的类型
from typing import Annotated  # 给 Query 参数附加约束的写法

from fastapi import APIRouter, HTTPException, Query, status  # 路由、异常、状态码
from sqlalchemy.ext.asyncio import AsyncSession  # 异步会话类型

from app.db import SessionDep  # 统一的数据库会话依赖
from app.deps import CurrentUser  # 从会话 Cookie 解出的登录用户
from app.models import Asset, EditSession, User  # 相关 ORM 模型
from app.schemas.agent import MessageIn, TurnOut  # 对话指令的出入参
from app.schemas.asset import AssetOut  # 素材出参
from app.schemas.session import (
    HistoryOut,
    SessionCreateIn,
    SessionDetailOut,
    SessionOut,
    SessionPatchIn,
)
from app.services import agent as agent_service  # 对话轮次的规划与落库
from app.services import assets as asset_service  # 素材查询（主键 + user_id 联合条件）
from app.services import sessions  # 会话业务逻辑
from app.services.sessions import SessionNotFound  # 会话不存在异常

router = APIRouter(prefix="/sessions", tags=["sessions"])


async def _asset(session: AsyncSession, user: User, asset_id: uuid.UUID) -> Asset:
    """按 id 取当前用户的素材，不存在返回 404（复用素材服务的 user_id 过滤）。"""
    asset = await asset_service.get_for_user(session, user.id, asset_id)
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "素材不存在")
    return asset


async def _load(session: AsyncSession, user: User, session_id: uuid.UUID) -> EditSession:
    """按 id 取当前用户的会话；不存在/别人的会话都返回 404，避免泄露资源存在性。"""
    try:
        return await sessions.get_for_user(session, session_id, user.id)
    except SessionNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "会话不存在") from exc


async def _detail(session: AsyncSession, record: EditSession) -> SessionDetailOut:
    """组装详情出参：会话本体 + 图片墙素材（签名 URL 等）。"""
    wall = await sessions.assets_of(session, record)
    return SessionDetailOut.of_detail(record, [AssetOut.of(asset) for asset in wall])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreateIn, user: CurrentUser, session: SessionDep
) -> SessionDetailOut:
    """新建会话：current 进入画布，asset_ids 里的其余素材一并进图片墙备选。"""
    current = await _asset(session, user, payload.current_asset_id)
    # 逐个校验归属；current 自己已在画布上，从墙的入参里剔除（_attach 也会去重，双保险）
    wall = [
        await _asset(session, user, asset_id)
        for asset_id in payload.asset_ids
        if asset_id != current.id
    ]

    record = await sessions.create(session, user.id, current, wall, payload.title)
    return await _detail(session, record)


@router.get("")
async def list_sessions(
    user: CurrentUser,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[SessionOut]:
    """当前用户的会话列表（按更新时间倒序），limit 限制条数 1~200。"""
    records = await sessions.list_for_user(session, user.id, limit)
    return [SessionOut.of(record) for record in records]


@router.get("/{session_id}")
async def get_session(
    session_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> SessionDetailOut:
    """会话详情：编辑页刷新/直链进入时用它恢复完整状态。"""
    return await _detail(session, await _load(session, user, session_id))


@router.patch("/{session_id}")
async def patch_session(
    session_id: uuid.UUID, payload: SessionPatchIn, user: CurrentUser, session: SessionDep
) -> SessionDetailOut:
    """部分更新：title 与 current_asset_id 都是可选，传了才改（可一次同时改两项）。"""
    record = await _load(session, user, session_id)

    if payload.title is not None:
        record = await sessions.rename(session, record, payload.title)
    if payload.current_asset_id is not None:
        asset = await _asset(session, user, payload.current_asset_id)
        record = await sessions.switch_current(session, record, asset)

    return await _detail(session, record)


@router.get("/{session_id}/history")
async def get_history(
    session_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> list[HistoryOut]:
    """编辑历史（最新在前），图层面板的「编辑记录」区使用。"""
    record = await _load(session, user, session_id)
    entries = await sessions.history_of(session, record)
    return [HistoryOut.of(entry) for entry in entries]


@router.get("/{session_id}/messages")
async def list_messages(
    session_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> list[TurnOut]:
    """会话的对话记录（按时间正序），侧栏打开会话时恢复整段对话。"""
    record = await _load(session, user, session_id)
    return [TurnOut.of(turn) for turn in await agent_service.turns_of(session, record)]


@router.post("/{session_id}/messages", status_code=status.HTTP_201_CREATED)
async def send_message(
    session_id: uuid.UUID, payload: MessageIn, user: CurrentUser, session: SessionDep
) -> TurnOut:
    """发送一条修图指令：同步规划并返回本轮结果（计划中的工具再经队列异步执行）。"""
    record = await _load(session, user, session_id)
    return TurnOut.of(await agent_service.respond(session, record, payload.text))
