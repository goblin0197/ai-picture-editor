"""编辑历史表 ORM 模型：记录会话内每一步画布操作。"""

import uuid  # 外键的 UUID 类型

from sqlalchemy import ForeignKey, String, UniqueConstraint  # 外键、VARCHAR、联合唯一约束
from sqlalchemy.dialects.postgresql import JSONB  # JSONB 列，存操作参数与结果
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # PG 原生 UUID 列类型
from sqlalchemy.orm import Mapped, mapped_column  # 映射类型注解与列构造器

from app.models.base import UUIDBase  # UUID 主键 + created_at 的基类

# 每个会话最多保留的历史条数：写入时把 seq 超限的旧行删掉（见 services/sessions._append_history）
HISTORY_LIMIT = 20


class EditHistory(UUIDBase):
    """线性编辑记录，只保留最近 HISTORY_LIMIT 条，不提供版本树与分支。

    「线性」：seq 单调递增，不做撤销树——这是刻意的能力取舍，换取实现简单。
    """

    __tablename__ = "edit_history"
    # (session_id, seq) 唯一：seq 在会话内连续编号，防并发写入撞号
    __table_args__ = (UniqueConstraint("session_id", "seq"),)

    # 归属用户外键：冗余存一份，删用户级联删历史
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # 所属会话：删会话级联删历史
    session_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("edit_sessions.id", ondelete="CASCADE"), index=True
    )
    seq: Mapped[int]  # 会话内序号，从 1 递增（倒序展示即「最新在前」）
    action: Mapped[str] = mapped_column(String(48))  # 动作名，如 create_session / switch_current
    params: Mapped[dict] = mapped_column(JSONB, default=dict)  # 动作入参（JSON）
    result: Mapped[dict] = mapped_column(JSONB, default=dict)  # 动作结果摘要（JSON）
