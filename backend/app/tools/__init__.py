"""工具注册表。新增工具在此登记即可同时对界面与 Agent 生效。"""

from app.tools.base import ToolSpec, UnknownTool  # 规格定义与未注册异常
from app.tools.generate import GENERATE_IMAGE  # 文生图工具

# 注册表本体：S 后续步骤（抠图、换背景、局部修改…）依次往这个元组里加
SPECS: tuple[ToolSpec, ...] = (GENERATE_IMAGE,)

# name → spec 的查询表，构建一次供 O(1) 查找
_BY_NAME = {spec.name: spec for spec in SPECS}


def spec_of(name: str) -> ToolSpec:
    """按名取规格；未注册抛 UnknownTool（agent 的 verify 环节会拦下并回复用户）。"""
    spec = _BY_NAME.get(name)
    if spec is None:
        raise UnknownTool(f"未注册的工具：{name}")
    return spec


def label_of(name: str) -> str:
    """工具的中文名；未注册的名字原样返回（用于拼答复文案）。"""
    return _BY_NAME[name].label if name in _BY_NAME else name


__all__ = ["GENERATE_IMAGE", "SPECS", "ToolSpec", "UnknownTool", "label_of", "spec_of"]
