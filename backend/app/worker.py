# ARQ 后台 worker 的入口配置。启动命令：uv run arq app.worker.WorkerSettings。
# 生成类接口只负责投递任务，真正的执行由这里加载的 worker 消费队列完成。
from arq.connections import RedisSettings

from app.config import get_settings
from app.tasks import TASKS

settings = get_settings()  # 模块加载时读一次配置，供下方 WorkerSettings 的类属性使用


class WorkerSettings:
    """ARQ worker 入口。新增异步任务需在 app.tasks.TASKS 中注册。"""

    # 从 redis_url 解析连接参数（含库号 db 2）；worker 与投递端必须连同一个库才能对上队列。
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = TASKS  # worker 注册表：只有列在 TASKS 里的函数才会被加载和消费
    max_jobs = 4  # 单个 worker 进程的最大并发任务数
    job_timeout = 300  # 单个任务超时上限（秒），超时会被判失败
    keep_result = 3600  # 任务结果在 Redis 中的保留时长（秒），即 arq:result:* 的 TTL
