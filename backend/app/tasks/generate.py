# 文生图的 ARQ 异步任务：worker 从 Redis 队列取到任务后执行的入口函数。
# “建记录→投递→消费”三步里的第三步；必须登记进 app/tasks/__init__.py 的 TASKS 才会被加载。
import logging
import uuid

from app.db import SessionFactory
from app.models.tool_run import RunStatus
from app.services import generation, runs

logger = logging.getLogger(__name__)  # 模块级 logger，兜底异常时记录堆栈便于排查


# ARQ 任务函数：签名固定为第一参数 ctx（worker 上下文）、其后是投递时传入的业务参数。
# 入参：ctx worker 上下文（此处用不到）；run_id 任务主键（投递时同时用作 job id）。
# 无返回值——结果通过 runs.finish 落库并经 SSE 广播，不靠返回值传递。
async def generate_images(ctx: dict, run_id: uuid.UUID) -> None:
    # 自建会话：worker 不在请求上下文里，没有 SessionDep 可注入，需自己开一个会话。
    async with SessionFactory() as session:
        try:
            run = await runs.load(session, run_id)  # 仅按主键加载（run_id 来自队列，已可信）
        except runs.RunNotFound:
            return  # 任务记录已不存在（如被删）：无事可做，直接返回
        # 队列重投或 worker 重启后的重复消费不应二次扣费
        # （投递用 run id 作 job id 已挡住大部分重复，这里再查终态做第二道防线）。
        if run.status.is_terminal:
            return

        try:
            await generation.execute(session, run)  # 真正的编排逻辑在 services/generation
        except Exception:
            # 任何遗漏的异常都必须落终态，否则订阅进度的客户端会一直空等
            # （generation.execute 内已兜底一层，这里防它自身抛出时兜底，是最后一道保险）。
            logger.exception("生成任务未捕获异常 run_id=%s", run_id)
            await session.rollback()  # 回滚半截事务，避免污染下面 finish 的提交
            await runs.finish(session, run, status=RunStatus.FAILED, error="生成失败，请重试")
