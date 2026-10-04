# 任务进度的 Redis 发布/订阅封装。设计取向：进度不落库轮询，而由状态变更方 publish、
# SSE 路由 subscribe 转推给前端。每个任务一个独立频道（run:<id>），发布订阅互不串扰。
import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from redis.asyncio import Redis

from app.config import get_settings

# 订阅端的空闲探测周期（秒）：这么久没消息就产出一次 None，供上层发 SSE 心跳、探测断线。
IDLE_TICK = 15.0


# @lru_cache：无参调用，令整个进程共享同一个 Redis 连接（含连接池），不必每次新建。
# decode_responses=True 让收到的消息直接是 str，省去手动 decode。
@lru_cache
def redis_client() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True)


# 私有：按 run_id 算出频道名。发布与订阅两端都经它取名，保证双方对齐同一频道。
def _channel(run_id: uuid.UUID) -> str:
    return f"run:{run_id}"


# 向某任务的频道发布一条状态快照。由 services/runs 在每次状态变更后调用。
# payload 是 JSON 化的状态字典（见 runs.snapshot）；这里序列化成字符串发出。
async def publish(run_id: uuid.UUID, payload: dict) -> None:
    await redis_client().publish(_channel(run_id), json.dumps(payload))


# @asynccontextmanager：把下面的异步生成器包装成 async with 可用的上下文管理器——
# yield 之前是进入时的准备（建订阅），finally 里是退出时的清理（退订并关闭），
# 无论调用方正常结束还是异常退出，都能保证释放订阅资源。
@asynccontextmanager
async def subscribe(run_id: uuid.UUID) -> AsyncIterator[AsyncIterator[dict | None]]:
    """订阅进度。空闲超过 IDLE_TICK 秒时产出 None，供调用方发送心跳。"""
    channel = _channel(run_id)
    pubsub = redis_client().pubsub()
    # 关键顺序：先 subscribe 建立订阅，调用方随后再去读一次数据库快照。
    # 反过来的话，任务若恰在“读快照”与“开始订阅”之间结束，那条终态消息就漏收、
    # 订阅端会一直空等；先订阅能保证这期间发布的消息都被频道接住。
    await pubsub.subscribe(channel)

    # 内部异步生成器：不断从订阅取消息并 yield 出去。
    async def messages() -> AsyncIterator[dict | None]:
        while True:
            # 带 timeout 的阻塞读：超时（IDLE_TICK 秒内无消息）返回 None，不会永久卡死。
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=IDLE_TICK)
            # 有消息就反序列化成字典 yield；空闲（message 为 None）则 yield None 供上层发心跳。
            yield json.loads(message["data"]) if message else None

    try:
        yield messages()  # 把消息流交给 async with 的调用方消费
    finally:
        await pubsub.aclose()  # 无论如何都退订并关闭，防止连接/订阅泄漏
