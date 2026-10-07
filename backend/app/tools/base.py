# 工具规格定义：一个 ToolSpec 就是「一个修图能力」的完整说明书。
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ToolRun

# 工具处理函数的统一签名：入参（会话、任务记录），返回结果 dict。
# 状态流转（start/finish）与异常兜底由 services/tools.execute 外壳负责，
# handler 只写业务逻辑——这是「外壳 + 处理函数」的分工约定。
ToolHandler = Callable[[AsyncSession, ToolRun], Awaitable[dict]]


class UnknownTool(Exception):
    # 引用了注册表里不存在的工具名（agent 的 verify 环节据此拦截）。
    pass


@dataclass(frozen=True)
class ToolSpec:
    """一个工具的完整定义，界面与 Agent 共用。

    params 同时用于服务端校验和生成模型的函数签名，两者不会漂移。
    handler 只关心业务结果，状态流转由统一的执行外壳负责。
    """

    name: str  # 工具标识（落 ToolRun.tool、Agent 计划里引用）
    label: str  # 中文短名（界面按钮与对话文案用）
    description: str  # 给规划模型的能力说明：何时该用/不该用
    params: type[BaseModel]  # 参数模型：服务端校验与模型函数签名共用它
    handler: ToolHandler  # 业务实现
    needs_approval: bool = False  # 是否需要用户确认后才执行（预留，本步未启用）
    # 素材 ID、随机种子这类参数应由服务端从上下文填入，不暴露给模型
    agent_hidden: tuple[str, ...] = field(default_factory=tuple)
