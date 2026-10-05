"""编辑会话的 Pydantic 出入参模型。"""

import uuid  # 各 id 字段类型
from datetime import datetime  # 时间戳字段类型
from typing import Annotated  # 给字段附加约束的类型注解写法

from pydantic import BaseModel, Field  # 模型基类与字段约束

from app.layers import LayerDocument  # 画布文档模型（校验 JSONB 里存的结构）
from app.models import EditHistory, EditSession  # 对应的 ORM 模型
from app.schemas.asset import AssetOut  # 素材出参（含签名 URL）

MAX_WALL_ASSETS = 12  # 建会话时图片墙入参的素材数上限


class SessionCreateIn(BaseModel):
    """建会话入参：current 进画布，asset_ids 里的其余素材一并进图片墙。"""

    current_asset_id: uuid.UUID  # 首张进入画布的素材
    # 同批未采用的候选一并进图片墙
    asset_ids: Annotated[list[uuid.UUID], Field(max_length=MAX_WALL_ASSETS)] = []
    title: str | None = None  # 可选标题；空/缺省由服务端归一为「未命名会话」


class SessionPatchIn(BaseModel):
    """改会话入参：两个都可选，传了才改（部分更新语义）。"""

    title: str | None = None
    current_asset_id: uuid.UUID | None = None


class SessionOut(BaseModel):
    """会话列表项：编辑页侧栏只需这些摘要字段，不必带文档与图片墙。"""

    id: uuid.UUID
    title: str
    revision: int  # 修订号：切图/采用候选时递增，前端可据此判断状态是否过期
    original_asset_id: uuid.UUID  # 会话源头素材
    current_asset_id: uuid.UUID  # 当前画布显示的素材
    created_at: datetime
    updated_at: datetime  # 会话列表按它倒序

    @classmethod
    def of(cls, record: EditSession) -> "SessionOut":
        """从 ORM 对象构造出参（本项目约定的 of 工厂模式）。"""
        return cls(
            id=record.id,
            title=record.title,
            revision=record.revision,
            original_asset_id=record.original_asset_id,
            current_asset_id=record.current_asset_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class SessionDetailOut(SessionOut):
    """会话详情：在摘要之上叠加画布文档与图片墙，编辑页工作区靠它恢复全部状态。"""

    document: LayerDocument  # 画布权威描述（Pydantic 校验 JSONB 内容的合法性）
    assets: list[AssetOut] = []  # 图片墙素材（含签名 URL），按挂载顺序

    @classmethod
    def of_detail(cls, record: EditSession, assets: list[AssetOut]) -> "SessionDetailOut":
        """先构造摘要部分，再展开叠加文档与图片墙。"""
        return cls(
            **SessionOut.of(record).model_dump(),
            document=LayerDocument.model_validate(record.document),
            assets=assets,
        )


class HistoryOut(BaseModel):
    """编辑历史条目：动作名 + 参数/结果原文，前端用 ACTION_LABELS 翻译动作名。"""

    seq: int  # 会话内序号，越大越新
    action: str  # 动作名，如 create_session / switch_current
    params: dict  # 动作入参（JSON）
    result: dict  # 动作结果摘要（JSON）
    created_at: datetime

    @classmethod
    def of(cls, entry: EditHistory) -> "HistoryOut":
        """从 ORM 对象构造出参。"""
        return cls(
            seq=entry.seq,
            action=entry.action,
            params=entry.params,
            result=entry.result,
            created_at=entry.created_at,
        )
