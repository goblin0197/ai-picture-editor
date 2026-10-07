# 对话指令的 Pydantic 出入参模型：POST /messages 的请求体与对话轮次出参。
import uuid  # 各 id 字段类型
from datetime import datetime  # 时间戳字段类型
from typing import Annotated  # 给字段附加约束的类型注解写法

from pydantic import BaseModel, Field, field_validator  # 模型基类、字段约束、校验器

from app.models import AgentRun  # 对应的 ORM 模型
from app.models.tool_run import RunStatus  # 复用任务状态枚举
from app.tools import label_of  # 工具名 → 中文标签

MAX_MESSAGE = 1000  # 单条指令最大长度


class MessageIn(BaseModel):
    """发消息入参：一段非空（去空白后）指令文本。"""

    text: Annotated[str, Field(min_length=1, max_length=MAX_MESSAGE)]

    @field_validator("text")
    @classmethod
    def _require_text(cls, value: str) -> str:
        # 去空白后为空视为纯空白输入，拒绝
        value = value.strip()
        if not value:
            raise ValueError("指令不能为空")
        return value


class PlanStepOut(BaseModel):
    """计划中的一步：工具名 + 中文标签 + 下发后的任务 id（未下发为 None）。"""

    tool: str
    label: str
    run_id: uuid.UUID | None = None

    @classmethod
    def of(cls, step: dict) -> "PlanStepOut":
        """从 AgentRun.plan 的 JSON dict 构造。"""
        return cls(tool=step["tool"], label=label_of(step["tool"]), run_id=step.get("run_id"))


class TurnOut(BaseModel):
    """一轮对话出参：指令、答复、规划状态与计划步骤。"""

    id: uuid.UUID
    revision: int  # 规划时基于的画布修订号
    goal: str
    reply: str
    status: RunStatus
    error: str | None
    created_at: datetime
    steps: list[PlanStepOut] = []

    @classmethod
    def of(cls, turn: AgentRun) -> "TurnOut":
        """从 ORM 对象构造，plan 逐项转成 PlanStepOut。"""
        return cls(
            id=turn.id,
            revision=turn.revision,
            goal=turn.goal,
            reply=turn.reply,
            status=turn.status,
            error=turn.error,
            created_at=turn.created_at,
            steps=[PlanStepOut.of(step) for step in turn.plan],
        )
