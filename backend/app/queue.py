# ARQ 任务投递入口（“建记录→投递→消费”的第二步）。接口侧调用这里把任务推进 Redis 队列，
# 真正的执行由 worker（app/worker.py）消费。核心约定：以 run id 作为 job id 保证幂等。
import uuid

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import get_settings

# 进程级连接池单例：首次用到时创建、之后复用，避免每次投递都新建连接。
_pool: ArqRedis | None = None


# 惰性获取共享连接池。首次调用建池，后续直接返回同一个。
async def queue() -> ArqRedis:
    global _pool
    if _pool is None:
        # 从 redis_url 解析连接参数（含库号 db 2）；worker 端必须连同一个库才能对上队列。
        _pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    return _pool


# 关闭并释放连接池，供应用关停时（lifespan 收尾）调用，避免连接泄漏。
async def close_queue() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


# 投递一个任务到队列。入参：task 任务名（须在 TASKS 中登记）；run_id 任务主键。
async def enqueue(task: str, run_id: uuid.UUID) -> None:
    """以 run id 作为任务 ID，重复投递同一 run 不会产生第二次执行。"""
    pool = await queue()
    # 关键：_job_id=str(run_id) 让 job id 等于 run id。ARQ 对同一 job id 去重，
    # 因此同一 run 即便被多次投递（重试、并发点击），队列里也只执行一次——这就是幂等。
    await pool.enqueue_job(task, run_id, _job_id=str(run_id))
