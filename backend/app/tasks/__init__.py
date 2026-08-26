# 异步任务的注册表模块。新增任务函数后，必须把它加进下面的 TASKS 列表，
# 否则 worker（app/worker.py 的 WorkerSettings.functions=TASKS）不会加载它、任务永不被消费。
from app.tasks.ping import ping
from app.tasks.tools import run_tool

# worker 注册表：WorkerSettings 直接引用它作为可消费的函数清单。顺序不影响功能。
# c200587 起 generate_images 被通用 run_tool 取代：所有工具共用一个任务入口，
# 具体执行由 tools 注册表按 run.tool 分发。
TASKS = [ping, run_tool]

# 模块公开接口：允许 from app.tasks import TASKS / ping / run_tool。
__all__ = ["TASKS", "ping", "run_tool"]
