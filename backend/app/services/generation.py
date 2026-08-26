# 文生图编排：具体工具的业务实现，串起「取参考图→调模型→转存候选图」并返回结果 dict。
# c200587 起状态流转与异常兜底上移到 services/tools.execute 统一外壳，本模块只关心业务结果；
# 「任何异常都必须落终态」的约束随之由外壳保证（订阅 SSE 的客户端不会空等）。
import uuid  # 参考图 id 的类型

from sqlalchemy.ext.asyncio import AsyncSession

from app import storage
from app.models.asset import AssetKind, AssetSource
from app.models.tool_run import ToolRun
from app.providers import GenerateRequest, ProviderError, get_image_provider
from app.ratios import Ratio, size_of
from app.services import assets, runs


# 私有：把任务参数里的参考图 id 逐个还原成图片字节。
# 入参：run（读 params.reference_asset_ids 与 user_id）。出参：字节列表。
# 仍按 user_id 联合查询防越权；缺失即抛 ProviderError（会被上层外壳落成失败终态）。
async def _references(session: AsyncSession, run: ToolRun) -> list[bytes]:
    result: list[bytes] = []
    for raw in run.params.get("reference_asset_ids") or []:
        asset = await assets.get_for_user(session, run.user_id, uuid.UUID(raw))
        if asset is None:
            raise ProviderError("参考图不存在")
        # 从对象存储取回原始字节，交给模型作参考图。
        result.append(await storage.get(asset.storage_key))
    return result


# worker 侧的工具实现。入参：session 会话；run 待执行任务。
# 返回结果 dict（asset_ids 列表）：落 succeeded 终态与图片墙记录由外壳完成。
async def execute(session: AsyncSession, run: ToolRun) -> dict:
    """执行一次文生图并把候选图转存为素材。

    模型返回的链接 24 小时过期，必须落到自有存储后再对外暴露。
    """

    # 进度回调：模型适配层通过它上报进度，转成 runs.report 落库并广播。
    async def on_progress(progress: int, stage: str) -> None:
        await runs.report(session, run, progress, stage)

    # 把声明的输出比例换算成具体像素宽高。
    width, height = size_of(Ratio(run.params["ratio"]))
    request = GenerateRequest(
        prompt=run.params["prompt"],
        width=width,
        height=height,
        count=run.params["count"],
        negative_prompt=run.params.get("negative_prompt"),
        seed=run.params.get("seed"),
        # 参考图内联为字节交给适配层（部分平台不支持参考图）。
        references=await _references(session, run),
    )

    # 调模型出图。get_image_provider 按配置返回具体适配器，调用方只认 Protocol。
    images = await get_image_provider().generate(request, on_progress)

    await runs.report(session, run, 90, "保存候选图")
    # 关键：模型返回的临时链接 24h 过期，这里立刻把字节转存进自有对象存储再返回，
    # 绝不把外部临时链接直接存进 result，否则事后候选图会失效打不开。
    created = [
        await assets.create_from_bytes(
            session, run.user_id, data, AssetKind.GENERATED, AssetSource.GENERATE
        )
        for data in images
    ]
    return {"asset_ids": [str(asset.id) for asset in created]}
