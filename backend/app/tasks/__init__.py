# 异步任务的注册表模块。新增任务函数后，必须把它加进下面的 TASKS 列表，
# 否则 worker（app/worker.py 的 WorkerSettings.functions=TASKS）不会加载它、任务永不被消费。
from app.tasks.generate import generate_images
from app.tasks.ping import ping

# worker 注册表：WorkerSettings 直接引用它作为可消费的函数清单。顺序不影响功能。
TASKS = [ping, generate_images]

# 模块公开接口：允许 from app.tasks import TASKS / generate_images / ping。
__all__ = ["TASKS", "generate_images", "ping"]
