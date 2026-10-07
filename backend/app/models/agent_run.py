# 对话轮次表 ORM 模型：编辑页左栏一次「指令 → 规划结果」的完整记录。
import uuid  # 外键的 UUID 类型

from sqlalchemy import ForeignKey, Text  # 外键与长文本列类型
from sqlalchemy.dialects.postgresql import JSONB  # JSONB 列，存规划出的计划
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # PG 原生 UUID 列类型
from sqlalchemy.orm import Mapped, mapped_column  # 映射类型注解与列构造器

from app.models.base import UUIDBase, enum_column  # UUID 主键基类与枚举列工厂
from app.models.tool_run import RunStatus  # 复用任务状态枚举


class AgentRun(UUIDBase):
    """一轮自然语言指令的规划结果，对应编辑页左栏的一次问答。

    status 只表示规划本身是否成功；计划中每一步的执行进度由其 ToolRun 承载。
    """

    __tablename__ = "agent_runs"

    # 归属用户：删用户级联删对话记录
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # 所属编辑会话：删会话级联删对话记录
    session_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("edit_sessions.id", ondelete="CASCADE"), index=True
    )
    # 规划所基于的修订号，用于判断执行时画布是否已被改动
    revision: Mapped[int]
    goal: Mapped[str] = mapped_column(Text)  # 用户的原始指令
    reply: Mapped[str] = mapped_column(Text, default="")  # 给用户的答复文案
    plan: Mapped[list] = mapped_column(JSONB, default=list)  # 规划出的步骤（tool/params/run_id）
    status: Mapped[RunStatus] = mapped_column(enum_column(RunStatus))  # 规划成败（非工具执行态）
    error: Mapped[str | None] = mapped_column(Text, default=None)  # 规划失败的原因
