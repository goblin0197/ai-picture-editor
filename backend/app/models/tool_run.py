# 任务表 ORM 模型：记录每次异步工具调用（如文生图）的状态、进度与结果
import enum  # 定义任务状态枚举 RunStatus
import uuid  # 外键 user_id 的 UUID 类型
from datetime import datetime  # started_at / finished_at 的时间类型

from sqlalchemy import ForeignKey, String, Text  # 外键、VARCHAR、长文本列类型
from sqlalchemy.dialects.postgresql import JSONB  # 以 JSONB 存参数与结果字典
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # PG 原生 UUID 列类型
from sqlalchemy.orm import Mapped, mapped_column  # 映射类型注解与列构造器

from app.models.base import TIMESTAMPTZ, UUIDBase, enum_column  # 时间列/基类/枚举列工厂


# 任务状态枚举：任务在队列与执行中的生命周期
class RunStatus(enum.StrEnum):
    QUEUED = "queued"  # 已投递、等待 worker 消费
    RUNNING = "running"  # worker 执行中
    SUCCEEDED = "succeeded"  # 成功（终态）
    FAILED = "failed"  # 失败（终态）
    CANCELED = "canceled"  # 已取消（终态）

    # @property：把方法暴露成只读属性，可用 status.is_terminal 直接取值
    @property
    def is_terminal(self) -> bool:
        # 是否为终态：worker 消费前用它做守卫，终态直接返回、防重复执行
        return self in {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELED}


class ToolRun(UUIDBase):
    """单次工具调用的执行记录。run id 同时作为队列任务 ID，重复投递不会重复执行。"""

    __tablename__ = "tool_runs"  # 表名 tool_runs

    # 归属用户外键：ondelete=CASCADE 使删用户时其任务一并删除；建索引便于按用户查询
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    tool: Mapped[str] = mapped_column(String(48))  # 工具名，如 "generate"（文生图）
    # 状态：默认 QUEUED（刚建记录尚未消费）；以 VARCHAR 存枚举 value
    status: Mapped[RunStatus] = mapped_column(enum_column(RunStatus), default=RunStatus.QUEUED)
    progress: Mapped[int] = mapped_column(default=0)  # 进度百分比 0-100，经 SSE 推送
    stage: Mapped[str] = mapped_column(String(64), default="")  # 当前阶段描述文案
    params: Mapped[dict] = mapped_column(JSONB, default=dict)  # 入参快照（JSONB）
    result: Mapped[dict] = mapped_column(JSONB, default=dict)  # 产出结果（JSONB）
    error: Mapped[str | None] = mapped_column(Text, default=None)  # 失败原因，成功时为空
    retries: Mapped[int] = mapped_column(default=0)  # 已重试次数
    # 开始/结束时间：入队时未开始故默认 None，带时区（TIMESTAMPTZ）
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, default=None)
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, default=None)
