# 健康检查路由：探测 API 自身、数据库、对象存储三方连通性，供部署侧存活/就绪探针使用。
import asyncio
from collections.abc import Awaitable

from fastapi import APIRouter
from sqlalchemy import text

from app import storage
from app.db import SessionDep

# 本模块路由前缀 /health；在 main.py 聚合时再套 /api，对外最终路径为 /api/health。
router = APIRouter(prefix="/health", tags=["health"])


# 通用探针：等待传入的 awaitable 完成。成功返回 "ok"，失败返回 "error: 异常类名"。
# 抽成独立函数，便于下面 health() 用 asyncio.gather 并发探测多个依赖。
async def _probe(awaitable: Awaitable) -> str:
    try:
        await awaitable
        return "ok"
    # 健康检查要如实报告任意故障，故此处刻意宽泛捕获所有异常。
    # BLE001 是 ruff 对「捕获过宽 Exception」的告警，此处有意为之，用带原因 noqa 保留豁免。
    except Exception as exc:  # noqa: BLE001 - 健康检查需要报告任意故障原因
        # 只回异常类型名、不回消息或堆栈，避免把内部细节泄露给探针调用方。
        return f"error: {type(exc).__name__}"


# 路由：GET /api/health，成功状态码 200（默认）。无需登录，供部署探针调用。
@router.get("")
# 职责：并发探测数据库与对象存储连通性并返回各自状态。
# 入参：session 注入的数据库会话。出参：api/database/storage 三个状态字段的字典。
# 注意：任一依赖故障仍返回 200，故障体现在字段值里（如 "error: xxx"），便于探针解析。
async def health(session: SessionDep) -> dict[str, str]:
    # 用 asyncio.gather 并发跑两个探针，缩短健康检查总耗时。
    database, object_storage = await asyncio.gather(
        # 数据库探针：执行最轻量的 select 1 验证连接可用。
        _probe(session.execute(text("select 1"))),
        # 存储探针：ensure_bucket 同步调用，用 to_thread 丢线程池避免阻塞事件循环。
        _probe(asyncio.to_thread(storage.ensure_bucket)),
    )
    return {"api": "ok", "database": database, "storage": object_storage}
