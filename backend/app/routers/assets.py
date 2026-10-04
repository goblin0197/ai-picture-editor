# 素材路由：上传、列出、按 id 查询。所有接口都要登录，且一律按 user_id 隔离。
import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.db import SessionDep
from app.deps import CurrentUser
from app.models.asset import AssetKind, AssetSource
from app.schemas.asset import AssetOut
from app.services import assets as asset_service
from app.services.images import MAX_FILE_BYTES, ImageRejected, probe

# 本模块路由前缀 /assets；经 main.py 套 /api 后对外为 /api/assets*。
router = APIRouter(prefix="/assets", tags=["assets"])


# 路由：POST /api/assets，成功状态码 201 Created。multipart 表单上传单文件。
@router.post("", status_code=status.HTTP_201_CREATED)
# 职责：接收上传图片，校验大小与格式后转存对象存储并落库。
# 入参：user 当前用户（登录守卫）；session 会话；file 表单文件。出参：AssetOut。
# 状态码：413 文件超限；422 图片非法；201 成功。
async def upload(
    user: CurrentUser,
    session: SessionDep,
    file: Annotated[UploadFile, File()],
) -> AssetOut:
    # 先整体读入内存再判断大小。
    data = await file.read()
    # 第一道闸：超过 20MB 直接 413，不进入解码，避免大文件拖垮内存/CPU。
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "文件超过 20 MB 上限")

    try:
        # 第二道闸：probe 以实际解码结果判定格式与尺寸，不采信扩展名/Content-Type。
        meta = probe(data)
    # 校验失败翻译成 422，并把具体原因（str(exc)）回给前端；from exc 保留异常链便于排查。
    except ImageRejected as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    # 原图入库：kind=ORIGINAL、source=UPLOAD，storage key 以 users/<user_id>/ 前缀隔离。
    asset = await asset_service.create_from_bytes(
        session, user.id, data, AssetKind.ORIGINAL, AssetSource.UPLOAD, meta
    )
    # AssetOut.of 会顺带签发图片的临时可访问 URL。
    return AssetOut.of(asset)


# 路由：GET /api/assets，成功状态码 200。
@router.get("")
# 职责：分页列出当前用户的素材（按创建时间倒序）。
# 入参：limit 每页条数，Query 约束 1..200，默认 50。出参：AssetOut 列表。
async def list_assets(
    user: CurrentUser,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[AssetOut]:
    # 仅查当前用户的素材，天然按 user_id 过滤。
    records = await asset_service.list_for_user(session, user.id, limit)
    return [AssetOut.of(asset) for asset in records]


# 路由：GET /api/assets/{asset_id}，成功状态码 200。
@router.get("/{asset_id}")
# 职责：按 id 取单个素材。入参 asset_id 路径参数；出参 AssetOut。
# 关键：查询走「主键 + user_id 联合条件」，访问他人素材时按 404 处理而非 403，
# 避免通过状态码差异泄露「该资源是否存在」。
async def get_asset(asset_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> AssetOut:
    asset = await asset_service.get_for_user(session, user.id, asset_id)
    # 查不到（不存在或不属于当前用户）一律 404。
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "素材不存在")
    return AssetOut.of(asset)
