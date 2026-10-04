# FastAPI 应用入口：装配生命周期钩子、聚合 /api 下的各路由、单独挂载 SSE，
# 并在生产环境用 StaticFiles 托管前端构建产物（实现前后端同源）。
import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

from app import storage
from app.config import get_settings
from app.queue import close_queue
from app.routers import assets, auth, events, health, runs

settings = get_settings()  # 模块加载时取一次配置，供下方判断是否托管前端等使用


# @asynccontextmanager：把「yield 之前=启动、之后=关闭」的异步函数变成上下文管理器，
# 交给 FastAPI 的 lifespan 参数，实现应用启停时各跑一段代码。
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动时确保对象存储桶存在，关闭时释放队列连接。"""
    # ensure_bucket 是同步的 boto3 调用，用 to_thread 丢到线程池，避免阻塞事件循环。
    await asyncio.to_thread(storage.ensure_bucket)
    yield  # ← 应用在此处正常对外提供服务，直到进程收到关闭信号
    await close_queue()  # 优雅关闭：释放 ARQ 投递用的 Redis 连接池


# 创建应用实例。文档与 OpenAPI 都放到 /api 前缀下，与「API 统一在 /api」的约定一致；
# lifespan 传入上面的生命周期管理器。
app = FastAPI(
    title="AI 修图智能体",
    docs_url="/api/docs",  # 交互式接口文档地址（Swagger UI）
    openapi_url="/api/openapi.json",  # OpenAPI 描述文件地址
    lifespan=lifespan,
)

# API 前缀只在这里集中声明一次：各 router 自身只写业务前缀（如 /health），
# 由这个带 prefix="/api" 的父路由统一加前缀，重复加会导致 404。
api = APIRouter(prefix="/api")
api.include_router(health.router)  # 健康检查（连通性自检）
api.include_router(auth.router)  # 账号注册/登录/当前用户
api.include_router(assets.router)  # 素材上传与管理
api.include_router(runs.router)  # 任务（生成等）状态查询
app.include_router(api)  # 把聚合后的 /api 路由挂到应用

# SSE 不挂在 /api 下，便于反向代理单独关闭缓冲
app.include_router(events.router)

# 生产环境下前端与 API 同源，静态产物由本服务托管；开发环境走 Vite dev proxy。
# 注意顺序：/api 与 /events 已在上面注册，最后才把 "/" 交给静态托管兜底，避免它吞掉接口路由。
# 目录不存在（未构建）时跳过挂载，此时后端照常启动，属预期行为。
if settings.frontend_dist.is_dir():
    # html=True：找不到具体文件时回退到 index.html，配合前端单页路由（SPA）刷新不 404。
    app.mount("/", StaticFiles(directory=settings.frontend_dist, html=True), name="frontend")
