# 规划模型（planner）：把工具注册表转成 function-calling 签名并绑定给 LLM。
# 工具的增减只改 tools 注册表，这里自动跟着变。
from functools import lru_cache

from langchain_core.utils.function_calling import convert_to_openai_function  # Pydantic→JSON Schema
from langchain_openai import ChatOpenAI  # OpenAI 兼容的对话模型客户端

from app.config import get_settings
from app.tools import SPECS, ToolSpec

# 图像模型必须走 DashScope 原生接口，纯文本的规划模型可用 OpenAI 兼容模式
_COMPATIBLE_PATH = "/compatible-mode/v1"


class PlannerUnavailable(Exception):
    """规划模型未配置或不可用。"""


def _schema_of(spec: ToolSpec) -> dict:
    """把工具规格转成 OpenAI function-calling 的工具描述。

    agent_hidden 里的参数（素材 id、随机种子等）由服务端从上下文填入，
    必须从给模型的 schema 里剔除——既防模型瞎填，也不泄露内部参数名。
    """
    function = convert_to_openai_function(spec.params)
    function["name"] = spec.name
    function["description"] = spec.description

    parameters = function.get("parameters", {})
    for hidden in spec.agent_hidden:
        parameters.get("properties", {}).pop(hidden, None)
    parameters["required"] = [
        name for name in parameters.get("required", []) if name not in spec.agent_hidden
    ]
    return {"type": "function", "function": function}


@lru_cache
def planner():
    """绑定全部已注册工具的规划模型。工具增减无需改动此处。

    lru_cache 让模型客户端进程内单例；测试里 monkeypatch graph.planner
    或改配置后需 planner.cache_clear()。
    """
    settings = get_settings()
    # 未配 Key 时明确报错而不是运行到一半失败
    if not settings.dashscope_api_key:
        raise PlannerUnavailable("未配置 DASHSCOPE_API_KEY，对话指令不可用")

    model = ChatOpenAI(
        model=settings.planner_model,
        api_key=settings.dashscope_api_key,
        base_url=f"{settings.dashscope_base_url}{_COMPATIBLE_PATH}",
        temperature=0,  # 规划要稳定可复现，不要发散
    )
    return model.bind_tools([_schema_of(spec) for spec in SPECS])
