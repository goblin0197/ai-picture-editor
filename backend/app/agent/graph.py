# 对话指令的执行图（langgraph）：plan → verify → dispatch 三节点。
# 核心安全设计：模型只负责「出主意」（产出计划），计划必须经服务端 verify 校验后
# 才允许真正下发——模型幻觉出的工具名/参数在这里被拦下。
import uuid  # AgentDeps 里各 id 的类型
from dataclasses import dataclass  # AgentDeps 的不可变数据类
from functools import lru_cache  # 图构建一次、进程内复用
from typing import TypedDict  # 图状态的结构声明

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage  # 消息类型
from langchain_core.runnables import RunnableConfig  # 节点间传递配置（带 deps）
from langgraph.graph import END, START, StateGraph  # 图的起止与构建器
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.llm import planner  # 规划模型（绑定全部已注册工具）
from app.services import tools as tool_service  # 工具校验与下发
from app.tools import UnknownTool, label_of, spec_of  # 工具注册表查询

# 系统提示词：约束模型的职责边界——一次只安排一步、参数自行推断、
# 做不到就说明原因而不是硬调工具；{context} 处填入画布事实摘要。
_SYSTEM = """你是电商图片修图助手，通过调用工具完成用户的修图请求。

规则：
- 只能使用已提供的工具，本轮最多安排一步。
- 缺失参数用画布信息与常识补齐，可推断的参数不要反问用户。
- 指令与修图无关，或现有工具做不到时，用一句中文说明原因，不要调用工具。

当前画布：{context}"""

# 模型没给出任何文字时的兜底答复（不编造成功）。
_FALLBACK_REPLY = "没太理解这条指令，换个说法或说得更具体一些。"


@dataclass(frozen=True)
class AgentDeps:
    """图执行所需的运行时依赖。不放进 state，以便后续接入 checkpoint。

    state 是要被图节点反复读写的业务数据；DB 会话这类重资源走 config 注入，
    二者分离后将来把 state 序列化做断点续跑（checkpoint）才不会拖泥带水。
    """

    session: AsyncSession
    user_id: uuid.UUID
    session_id: uuid.UUID


class AgentState(TypedDict):
    """图状态：goal 用户指令；context 画布事实；plan 校验后的计划；reply 给用户的答复。"""

    goal: str
    context: str
    plan: list[dict]
    reply: str


async def _plan(state: AgentState) -> AgentState:
    """节点一：把系统提示（含画布事实）与用户指令交给规划模型，取回工具调用计划。"""
    message = await planner().ainvoke(
        [
            SystemMessage(_SYSTEM.format(context=state["context"])),
            HumanMessage(state["goal"]),
        ]
    )
    return {
        # tool_calls 是模型在 function-calling 协议下给出的结构化调用清单
        "plan": [{"tool": call["name"], "params": call["args"]} for call in message.tool_calls],
        "reply": _text_of(message),  # 模型可能同时给一句自然语言答复
    }


def _verify(state: AgentState) -> AgentState:
    """模型给出的计划一律经服务端校验，不可直接执行。

    工具名必须在注册表内、参数必须过该工具自己的 Pydantic 模型；
    任一步不合法则整体放弃执行，把原因作为答复返回。
    """
    checked: list[dict] = []
    for step in state["plan"]:
        try:
            spec = spec_of(step["tool"])
            params = tool_service.validate(spec.name, step["params"])
        except (UnknownTool, tool_service.InvalidParams) as exc:
            return {"plan": [], "reply": f"这一步暂时执行不了：{exc}"}
        checked.append({"tool": spec.name, "params": params})
    return {"plan": checked}


async def _dispatch(state: AgentState, config: RunnableConfig) -> AgentState:
    """节点三：把校验过的每一步真正下发（建 ToolRun + 投队列），执行交给 worker。"""
    deps: AgentDeps = config["configurable"]["deps"]

    plan: list[dict] = []
    for step in state["plan"]:
        run = await tool_service.submit(
            deps.session, deps.user_id, step["tool"], step["params"], deps.session_id
        )
        plan.append(step | {"run_id": str(run.id)})  # run_id 回填进计划，前端据此订阅进度

    labels = "、".join(label_of(step["tool"]) for step in plan)
    return {"plan": plan, "reply": state["reply"] or f"好，正在{labels}。"}


def _has_plan(state: AgentState) -> str:
    """条件边：有计划去 dispatch，没有（被 verify 拦下或模型只回话）直接结束。"""
    return "dispatch" if state["plan"] else END


@lru_cache
def _graph():
    """构建并编译执行图。结构固定，进程内只构建一次。"""
    builder = StateGraph(AgentState)
    builder.add_node("plan", _plan)
    builder.add_node("verify", _verify)
    builder.add_node("dispatch", _dispatch)

    builder.add_edge(START, "plan")
    builder.add_edge("plan", "verify")
    builder.add_conditional_edges("verify", _has_plan, {"dispatch": "dispatch", END: END})
    builder.add_edge("dispatch", END)
    return builder.compile()


async def run(goal: str, context: str, deps: AgentDeps) -> tuple[str, list[dict]]:
    """规划并下发一轮指令，返回给用户的答复与已下发的计划。"""
    state = await _graph().ainvoke(
        {"goal": goal, "context": context, "plan": [], "reply": ""},
        config={"configurable": {"deps": deps}},  # deps 经 config 注入，不进 state
    )
    # 模型空答复时用兜底文案，绝不无中生有地宣称已执行
    return state["reply"] or _FALLBACK_REPLY, state["plan"]


def _text_of(message: AIMessage) -> str:
    """从模型回复里取纯文本：兼容字符串与分块两种 content 形态。"""
    if isinstance(message.content, str):
        return message.content.strip()
    # 部分模型返回分块内容，只取文本块
    return "".join(
        block.get("text", "") for block in message.content if isinstance(block, dict)
    ).strip()
