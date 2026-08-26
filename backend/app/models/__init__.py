"""模型包。新增模型后需在此导出，供 Alembic autogenerate 发现。"""

# 导入各表模型：仅导入即可让 SQLAlchemy 注册到 Base.metadata，
# Alembic 据此对比生成迁移；漏导入会导致 autogenerate 发现不到该表
from app.models.agent_run import AgentRun  # 对话轮次表（自然语言指令的规划结果）
from app.models.asset import Asset  # 素材表
from app.models.edit_history import EditHistory  # 编辑历史表（每步画布操作一条）
from app.models.edit_session import EditSession, SessionAsset  # 编辑会话表与会话-素材关联表
from app.models.tool_run import ToolRun  # 任务表
from app.models.user import User  # 账号表

# 对外导出的公共名单：控制 from app.models import * 的可见符号
__all__ = [
    "AgentRun",
    "Asset",
    "EditHistory",
    "EditSession",
    "SessionAsset",
    "ToolRun",
    "User",
]
