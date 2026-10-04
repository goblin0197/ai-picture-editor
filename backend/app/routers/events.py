# SSE 进度推送路由：以 Server-Sent Events 向前端实时推送任务进度。
# 注意本模块挂在 /events（不在 /api 下），便于反向代理单独关闭缓冲。
import asyncio
import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from app import events
from app.db import SessionDep
from app.deps import CurrentUser
from app.models.tool_run import RunStatus
from app.services import runs
from app.services.runs import RunNotFound

# 前缀 /events（有意不在 /api 下）；vite.config.ts 也把 /events 代理到后端，两边要同步改。
router = APIRouter(prefix="/events", tags=["events"])

# SSE 响应头：no-cache 禁缓存；X-Accel-Buffering=no 关掉 Nginx 缓冲，让帧即时下发。
_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}

# 超时后主动断开，客户端重连时会先收到快照，不会丢状态
_MAX_STREAM_SECONDS = 600.0


# 私有：把 payload 打包成一帧 SSE 文本。
# SSE 帧格式固定为 data: <内容> 加空行结束；ensure_ascii=False 保留中文。
def _frame(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# 路由：GET /events/runs/{run_id}，返回 text/event-stream 长连接。需登录。
@router.get("/runs/{run_id}")
# 职责：先校验任务归属，再以 SSE 持续推送该任务的进度快照与后续变更。
# 入参：run_id 路径参数；user 登录守卫；session 会话。出参：StreamingResponse。
async def stream_run(run_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> Response:
    # 建流前先鉴权+校验归属：他人/不存在的任务按 404，避免越权订阅。
    try:
        await runs.get(session, run_id, user.id)
    except RunNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "任务不存在") from exc

    # 内部生成器：被 StreamingResponse 持续拉取，每 yield 一次就下发一帧。
    async def stream() -> AsyncIterator[str]:
        # 先订阅再读快照，否则任务在两步之间结束会让连接一直空等
        # （若反过来，任务恰在读快照与开始订阅之间结束，就会漏掉终态帧、连接空等）。
        async with events.subscribe(run_id) as messages:
            # 订阅建立后立刻发一帧当前快照，保证刷新/重连的客户端马上拿到最新状态。
            run = await runs.get(session, run_id, user.id)
            yield _frame(runs.snapshot(run))
            # 若任务已是终态，发完快照即结束，无需再等后续帧。
            if run.status.is_terminal:
                return

            # 连接存活上限，到点主动断开（客户端会重连并重新拿快照）。
            deadline = asyncio.get_running_loop().time() + _MAX_STREAM_SECONDS
            # 消费订阅：有消息转成 SSE 帧；空闲时 subscribe 会周期性产出 None。
            async for payload in messages:
                # payload 为 None 表示这段空闲无新消息。
                if payload is None:
                    # 超过存活上限则收尾断开。
                    if asyncio.get_running_loop().time() > deadline:
                        return
                    # 否则发一条 SSE 注释行心跳（以冒号开头即注释帧），保活并探测断线。
                    yield ": ping\n\n"
                    continue
                # 正常进度帧，透传给客户端。
                yield _frame(payload)
                # 收到终态帧后服务端主动结束流，不再空挂连接。
                if RunStatus(payload["status"]).is_terminal:
                    return

    # media_type=text/event-stream 是 SSE 的约定类型；带上前面定义的禁缓冲响应头。
    return StreamingResponse(stream(), media_type="text/event-stream", headers=_HEADERS)
