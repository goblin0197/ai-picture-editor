# 工具执行中枢：参数校验、任务下发与统一执行外壳。
# 界面（routers/runs.py）与 Agent（agent/graph.py）都从这里走，「建记录→投递→消费」三步收拢于此。
import logging
import uuid

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Asset, ToolRun
from app.models.tool_run import RunStatus
from app.providers import ProviderError
from app.queue import enqueue
from app.services import assets, runs, sessions
from app.tools import UnknownTool, spec_of

# ARQ 任务名：worker 侧 tasks/tools.py 的 run_tool 按 run.tool 分发到具体工具
TASK = "run_tool"

logger = logging.getLogger(__name__)


class InvalidParams(Exception):
    # 参数不合法。message 已整理成「字段：原因」，可直接展示给用户/模型。
    pass


def validate(tool: str, params: dict) -> dict:
    """按工具自己的模型校验参数，界面与 Agent 走同一套规则。"""
    spec = spec_of(tool)
    try:
        # 校验通过的同时归一化输出（mode="json" 保证 UUID 等可序列化）
        return spec.params.model_validate(params).model_dump(mode="json")
    except ValidationError as exc:
        raise InvalidParams(_first_error(exc)) from exc


async def submit(
    session: AsyncSession,
    user_id: uuid.UUID,
    tool: str,
    params: dict,
    session_id: uuid.UUID | None = None,
) -> ToolRun:
    """下发一个工具任务：校验参数 → 建记录 → 投队列。job id = run.id（幂等）。"""
    run = await runs.create(session, user_id, tool, validate(tool, params), session_id)
    await enqueue(TASK, run.id)
    return run


async def execute(session: AsyncSession, run: ToolRun) -> None:
    """统一的执行外壳：状态流转与失败兜底集中在此，具体工具只返回结果。

    「任何异常都必须落终态」的约束由这里保证（订阅 SSE 的客户端不会空等）。
    """
    try:
        spec = spec_of(run.tool)
        await runs.start(session, run)
        # 具体业务（如 generation.execute）只产出结果 dict，不碰状态
        result = await spec.handler(session, run)
        await _record(session, run, result)
    except (ProviderError, UnknownTool) as exc:
        # 已知失败：消息可理解，直接透传给前端
        await runs.finish(session, run, status=RunStatus.FAILED, error=str(exc))
    except Exception:
        # 兜底：未预期异常也要落终态；记完整堆栈、回滚半截事务、对外笼统提示
        logger.exception("工具执行异常 tool=%s run_id=%s", run.tool, run.id)
        await session.rollback()
        await runs.finish(session, run, status=RunStatus.FAILED, error="执行失败，请重试")
    else:
        await runs.finish(session, run, status=RunStatus.SUCCEEDED, result=result)


async def _record(session: AsyncSession, run: ToolRun, result: dict) -> None:
    """把工具产出并入发起会话的图片墙并写编辑记录；无会话（创作页发起）则跳过。"""
    if run.session_id is None:
        return

    try:
        record = await sessions.load(session, run.session_id)
    except sessions.SessionNotFound:
        return  # 会话已被删除：产出素材仍存在，只是不进任何墙

    produced: list[Asset] = []
    for raw in result.get("asset_ids", []):
        asset = await assets.get_for_user(session, run.user_id, uuid.UUID(raw))
        if asset is not None:
            produced.append(asset)

    await sessions.record_result(session, record, produced, run.tool, run.params, result)


def _first_error(exc: ValidationError) -> str:
    """取第一条校验错误，整理成「字段：原因」的短文案。"""
    error = exc.errors()[0]
    field = ".".join(str(part) for part in error["loc"]) or "参数"
    return f"{field}：{error['msg']}"
