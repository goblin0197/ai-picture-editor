# 任务路由：提交文生图任务、查询任务状态与候选图。走「建记录→投递→worker 消费」三步。
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionDep
from app.deps import CurrentUser
from app.models.tool_run import ToolRun
from app.queue import enqueue
from app.schemas.asset import AssetOut
from app.schemas.run import GenerateIn, RunOut
from app.services import assets as asset_service
from app.services import generation, runs
from app.services.runs import RunNotFound

# 本模块不设业务前缀（tags 仅用于文档分组），具体路径写在各装饰器上；
# 经 main.py 套 /api 后对外为 /api/generations 与 /api/runs/{id}。
router = APIRouter(tags=["runs"])


# 私有辅助：把任务 result 里记录的 asset_id 还原成带签名 URL 的 AssetOut 列表。
# 入参：session 会话；run 任务记录。出参：候选素材列表（可能为空）。
async def _candidates(session: AsyncSession, run: ToolRun) -> list[AssetOut]:
    """候选图的签名 URL 有有效期，每次读取时重新签发。"""
    result = []
    # asset_ids 是生成成功后 worker 写进 result 的候选图主键列表。
    for raw in run.result.get("asset_ids", []):
        # 仍按 user_id 联合查询防越权；AssetOut.of 每次都会重签一次短时 URL。
        asset = await asset_service.get_for_user(session, run.user_id, uuid.UUID(raw))
        # 素材可能已被删，跳过缺失项而非报错。
        if asset is not None:
            result.append(AssetOut.of(asset))
    return result


# 路由：POST /api/generations，成功状态码 202 Accepted（任务已受理，异步执行）。
@router.post("/generations", status_code=status.HTTP_202_ACCEPTED)
# 职责：校验参考图归属→建任务记录→投递队列→立即返回，不同步等结果。
# 入参：payload 生成参数（含参考图 id）；user 当前用户；session 会话。出参：RunOut。
# 状态码：参考图不属于当前用户/不存在时 404；受理成功 202。
async def create_generation(payload: GenerateIn, user: CurrentUser, session: SessionDep) -> RunOut:
    # 逐个校验参考图归属：get_for_user 联合 user_id，防止引用他人素材，缺失即 404。
    for asset_id in payload.reference_asset_ids:
        if await asset_service.get_for_user(session, user.id, asset_id) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "参考图不存在")

    # 把入参序列化成可 JSON 存储的 dict，落进 ToolRun.params 供 worker 读取。
    params = payload.model_dump(mode="json")
    # 第一步：建任务记录，初始状态 queued。
    run = await runs.create(session, user.id, generation.TOOL, params)
    # 第二步：投递队列，以 run.id 作为 job id 保证幂等（重复投递不会二次执行）。
    # 真正的生成在 worker 侧 generate_images 任务里跑，只起后端会一直停在 queued。
    await enqueue("generate_images", run.id)
    return RunOut.of(run)


# 路由：GET /api/runs/{run_id}，成功状态码 200。用于刷新/恢复任务状态与候选图。
@router.get("/runs/{run_id}")
# 职责：查任务并附带候选图。入参 run_id 路径参数；出参 RunOut（含候选列表）。
# 关键：runs.get 联合 user_id 查询，他人任务按 404 处理，不泄露其是否存在。
async def get_run(run_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> RunOut:
    try:
        run = await runs.get(session, run_id, user.id)
    # 领域异常 RunNotFound 翻译成 404；from exc 保留异常链。
    except RunNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "任务不存在") from exc
    # 每次读取都重新签发候选图 URL，避免返回已过期的链接。
    return RunOut.of(run, await _candidates(session, run))
