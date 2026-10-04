# 任务（ToolRun）状态管理：建记录、查询与状态流转。每次状态变更都经 Redis 广播给 SSE。
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import events
from app.models.tool_run import RunStatus, ToolRun


# 领域异常：任务不存在或不属于当前用户。由 get/load 抛出，路由层翻译成 404。
class RunNotFound(Exception):
    pass


# 把任务压成可 JSON 化的状态快照，用于 SSE 首帧与每次变更的广播 payload。
# 字段与前端消费的进度模型一一对应。
def snapshot(run: ToolRun) -> dict:
    return {
        "id": str(run.id),
        "tool": run.tool,
        "status": run.status,
        "progress": run.progress,
        "stage": run.stage,
        "error": run.error,
    }


# 建任务记录（状态默认 queued），refresh 拿回数据库生成的字段（id、时间戳等）。
# 「建记录→投递→消费」三步里的第一步。入参：user_id/tool/params；出参：落库后的 ToolRun。
async def create(session: AsyncSession, user_id: uuid.UUID, tool: str, params: dict) -> ToolRun:
    run = ToolRun(user_id=user_id, tool=tool, params=params, stage="等待开始")
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


# 按「run_id + user_id」联合查询任务，查不到抛 RunNotFound（路由层转 404，防越权）。
# 供路由层查询任务、校验 SSE 订阅归属使用。
async def get(session: AsyncSession, run_id: uuid.UUID, user_id: uuid.UUID) -> ToolRun:
    run = await session.scalar(
        select(ToolRun).where(ToolRun.id == run_id, ToolRun.user_id == user_id)
    )
    if run is None:
        raise RunNotFound
    return run


# 仅按主键加载任务、不校验归属，仅供 worker 内部使用（run_id 由队列传入，已可信）。
# 查不到同样抛 RunNotFound。
async def load(session: AsyncSession, run_id: uuid.UUID) -> ToolRun:
    run = await session.get(ToolRun, run_id)
    if run is None:
        raise RunNotFound
    return run


# 私有：提交事务后立刻把最新快照广播到 Redis 频道。
# 「先落库再广播」保证订阅者收到的状态与库一致；进度不落库轮询，而用发布订阅推送。
async def _commit(session: AsyncSession, run: ToolRun) -> None:
    await session.commit()
    await events.publish(run.id, snapshot(run))


# 状态流转：queued → running，记录开始时间并给个初始进度。worker 领取任务时调用。
async def start(session: AsyncSession, run: ToolRun) -> None:
    run.status = RunStatus.RUNNING
    run.started_at = datetime.now(UTC)
    run.progress = 5
    run.stage = "已开始"
    await _commit(session, run)


# 上报中途进度。progress 取 max 保证单调不回退（乱序回调不会让进度倒退）。
# 每次调用都经 _commit 落库并广播。
async def report(session: AsyncSession, run: ToolRun, progress: int, stage: str) -> None:
    run.progress = max(run.progress, progress)
    run.stage = stage
    await _commit(session, run)


# 状态流转到终态：succeeded / failed / canceled。写入结果或错误、补齐进度与结束时间。
# 用 * 强制后续参数按关键字传，避免 status/result/error 传错位置。
# 无论成功失败都必须落终态，否则订阅 SSE 的客户端会一直空等。
async def finish(
    session: AsyncSession,
    run: ToolRun,
    *,
    status: RunStatus,
    result: dict | None = None,
    error: str | None = None,
) -> None:
    run.status = status
    run.result = result or {}
    run.error = error
    # 成功才补到 100%；失败保留当时进度，便于看出卡在哪一步。
    run.progress = 100 if status is RunStatus.SUCCEEDED else run.progress
    run.stage = "已完成" if status is RunStatus.SUCCEEDED else "已结束"
    run.finished_at = datetime.now(UTC)
    await _commit(session, run)
