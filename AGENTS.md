# AGENTS.md

本文件为 ZCode 等编码代理提供本仓库的上下文与硬性约定。**所有代码注释、提交信息、UI 文案一律使用中文。**

## 项目定位

AI 修图智能体（compose 项目名 `ai-retouch-agent`）：一句话生成商品图，或上传图片后继续编辑，自动串联抠图、换背景、局部修改与多尺寸导出。

当前进度：本地基础设施、健康检查、ARQ 投递链路、前端外壳、**账号注册登录**、**素材上传与对象存储**已就绪；生成、编辑、批量、导出尚未实现，`/editor`、`/batch` 等仍为占位页并标注了计划中的开发步骤编号（S4、S11 等）。

## 目录结构

| 路径 | 说明 |
| --- | --- |
| `backend/app/main.py` | FastAPI 入口，`lifespan` 中建桶，挂载 `/api` 路由与前端静态产物 |
| `backend/app/config.py` | `Settings`（pydantic-settings），从**仓库根目录** `.env` 读取 |
| `backend/app/db.py` | 异步引擎、`Base`、`SessionDep` 依赖 |
| `backend/app/deps.py` | `CurrentUser` 依赖，从会话 Cookie 解出当前用户 |
| `backend/app/security.py` | 密码哈希（bcrypt）与 JWT 会话令牌签发/解析 |
| `backend/app/storage.py` | 对象存储封装（boto3/S3），`ensure_bucket` 与签名 URL |
| `backend/app/routers/` | 路由模块，每个模块自带 `prefix` 与 `tags` |
| `backend/app/services/` | 业务逻辑（`auth` 账号、`assets` 素材、`images` 图片校验） |
| `backend/app/schemas/` | Pydantic 出参模型，`XxxOut.of(orm_obj)` 从 ORM 对象构造 |
| `backend/app/tasks/` | ARQ 异步任务，`__init__.py` 的 `TASKS` 列表即 worker 注册表 |
| `backend/app/models/` | SQLAlchemy ORM 模型，`base.py` 提供 `UUIDBase`（uuid 主键 + `created_at`） |
| `backend/migrations/versions/` | Alembic 迁移脚本，文件名 `日期_序号_描述.py` |
| `backend/tests/` | pytest 测试（`asyncio_mode = "auto"`，直接用顶层 `async def`） |
| `frontend/src/api/` | `client.ts` 是通用请求出口；`auth.ts`/`assets.ts` 是分领域封装 |
| `frontend/src/hooks/` | React Query 封装（`useAuth`、`useAssets`），含查询键与失效策略 |
| `frontend/src/components/` | 可复用组件（`AssetCard`、`ImageDropzone`） |
| `frontend/src/index.css` | Tailwind v4 `@theme` 设计令牌（**无 tailwind.config.js**） |
| `docs/` | 方案与过程文档，**已被 `.gitignore` 忽略**，克隆后不存在 |

## 端口分配

前端与后端使用非默认端口。三个共享基础设施优先用各自的默认端口，默认端口被占用时顺延（当前只有 PostgreSQL 需要顺延）。

| 服务 | 端口 | 归属 |
| --- | --- | --- |
| 前端 Vite dev | 7301 | 本仓库 |
| 后端 API | 7302 | 本仓库 |
| PostgreSQL | **5433**（默认 5432 已被其他项目占用） | 共享服务（`~/Desktop/postgres`） |
| Redis | 6379，本项目占用 **db 2** | 共享服务（`~/Desktop/redis`） |
| MinIO S3 API / 控制台 | 9000 / 9001 | 共享服务（`~/Desktop/minio`） |

共享服务均以 host 网络运行并监听 `0.0.0.0`，家庭内网的其他设备可直接连接（本机用 `127.0.0.1`，局域网用 `192.168.1.100`）。注意 PostgreSQL 从局域网连接必须带密码，本机回环则免密。`db 0` 与 `db 1` 已被其他项目占用，本项目固定用 `db 2`；新增接入项目请另选空闲库号，不要改本项目的库号。库号分配台账与各项目占用情况见 `~/Desktop/redis/README.md`（MinIO 桶约定见 `~/Desktop/minio/README.md`，PostgreSQL 认证规则见 `~/Desktop/postgres/README.md`）。

## 常用命令

**开发环境不使用 Docker 运行前后端**：后端用 `uv run uvicorn`、前端用 `npm run dev` 直接在本机跑（热重载也依赖这种方式）。Docker 只承载下面三个基础设施共享服务。

基础设施不在本仓库的 compose 内，而是本机独立共享服务，供本机与家庭内网多个项目复用，启停在各自目录下操作：

```bash
docker compose -f ~/Desktop/postgres/docker-compose.yml up -d
docker compose -f ~/Desktop/redis/docker-compose.yml up -d
docker compose -f ~/Desktop/minio/docker-compose.yml up -d
```

本仓库的 compose 只包含**部署**用的 `app` 与 `worker`（`docker compose --profile deploy up -d`），开发时不要用。
注意**不带 profile 时没有任何服务被选中**，`docker compose up -d` 会静默输出 `no service selected` 而不做任何事（退出码仍是 0），别把它当成基础设施已启动。

后端（全部在 `backend/` 目录下执行）：

```bash
uv sync --all-extras                      # 首次；--all-extras 才会装上 cv / agent 可选依赖
uv run uvicorn app.main:app --reload --port 7302
uv run arq app.worker.WorkerSettings      # worker
uv run pytest                             # 测试
uv run ruff check .                       # lint（line-length 100，规则 E/F/I/UP/B）
uv run alembic revision --autogenerate -m "描述"
uv run alembic upgrade head
```

前端（在 `frontend/` 下执行，需 Node 22+）：

```bash
npm ci
npm run dev      # → http://localhost:7301
npm run build    # tsc -b && vite build，类型错误会中断构建
npm run lint     # oxlint
```

## 架构边界与硬性约定

**前后端始终同源。** 生产环境由 FastAPI 以 `StaticFiles` 在 `/` 托管 `frontend/dist`；开发环境由 Vite 代理 `/api` 与 `/events` 到 7302。因此前端必须使用相对路径（`/api/...`、`/events`），**不要硬编码绝对地址或引入 CORS 配置**——httpOnly Cookie 与 SSE 正是依赖同源才能零配置工作。

**API 前缀只在 `main.py` 集中声明。** `main.py` 用 `APIRouter(prefix="/api")` 聚合各 router，路由模块自身只写业务前缀（如 `/health`），重复添加 `/api` 会导致 404。接口文档在 `/api/docs`。

**新增异步任务必须注册。** 在 `app/tasks/` 写函数后，追加到 `app/tasks/__init__.py` 的 `TASKS` 列表，否则 worker 不会加载。任务签名固定为 `async def fn(ctx: dict)`。

**新增 ORM 模型必须在 `app/models/__init__.py` 导出**，否则 Alembic autogenerate 发现不到该表。

**Alembic 连接串来自应用配置**（`migrations/env.py` 调用 `get_settings().database_url`），`alembic.ini` 中不配置 `sqlalchemy.url`，不要在那里填写连接信息。

**配置来源统一。** `Settings` 读取仓库根目录的 `.env`（`.env.example` 是模板，已被 `.gitignore` 忽略实际 `.env`），字段名小写、环境变量名大写无前缀（`IMAGE_PROVIDER` → `image_provider`）。`get_settings()` 带 `lru_cache`，测试中如需改配置要清缓存。

**数据库会话通过 `SessionDep` 注入**（`app/db.py` 的 `Annotated[AsyncSession, Depends(get_session)]`），不要自行创建 session。

**认证依赖 `CurrentUser`。** 需要登录的接口注入 `app/deps.py` 的 `CurrentUser`（`Annotated[User, Depends(...)]`），它从 `session` Cookie 解析 JWT；无效一律按 401 处理。会话 Cookie 是 `HttpOnly; SameSite=lax`，前端拿不到也不该去读它——判断登录态走 `useAuth` 的 `useCurrentUser`（未登录时后端返回 401，前端据此视为未认证）。

**素材接口一律按 `user_id` 过滤。** 查询素材必须用 `services/assets.get_for_user` 这类「主键 + user_id 联合条件」的方式，返回 404 而非 403，避免泄露他人资源是否存在；对象存储的 key 也以 `users/<user_id>/` 为前缀隔离。

**对象存储经 `app/storage.py` 访问，不要直接调 boto3。** 该模块用 `lru_cache` 复用客户端，并把同步调用包在 `asyncio.to_thread` 里；桶在 `main.py` 的 `lifespan` 中自动创建（`ensure_bucket`），无需手工建桶。对外一律用签名 URL（`signed_url`），不回传原始对象直链。

**图片校验在 `services/images.py` 的 `probe()` 内集中处理**（大小、格式、最小边长、像素总量），格式以**实际解码结果**为准而非文件扩展名或客户端 Content-Type。新增图片入口请复用该函数，不要在各 router 里重复校验。

**图像提供方默认 `mock`**，使用本地占位图、不产生调用费用；切到 `dashscope` 才走真实模型（`qwen-image-3.0-pro` / `qwen-image-edit-max` / `qwen-plus`）。开发与测试不要擅自改动该开关或消耗真实额度。

## 编码规范

后端：

- Ruff 负责格式化与 lint，提交前跑 `uv run ruff check .`。
- 已知必须保留的例外用带原因的 `# noqa: <rule> - 中文原因`，参见 `app/routers/health.py` 中的 `BLE001`。
- 类型注解完整；`Settings` 类只声明带默认值的字段。

前端：

- `tsconfig.app.json` 开启了 `verbatimModuleSyntax`（类型导入必须写 `import type`）、`noUnusedLocals`、`noUnusedParameters`、`erasableSyntaxOnly`，构建即类型检查。
- 路径别名 `@` → `frontend/src` 在 `vite.config.ts` 与 `tsconfig.app.json` **两处各配一份**，改动时必须同步。
- 样式使用 `src/index.css` `@theme` 中的语义令牌（颜色如 `text-ink`、`bg-paper`、`border-line`、`bg-brand-soft`、`text-muted`，圆角如 `rounded-control`/`rounded-card`，阴影如 `shadow-card`），不要引入新的原始色值或另建配置文件。现有组件多用等价的行内写法（如 `rounded-[12px]`、`text-[10px]` 之外的颜色一律走令牌）。
- 服务端状态用 `@tanstack/react-query`，请求统一走 `@/api/client` 的 `api`；错误已归一化为 `ApiError`（携带 `status` 与后端 `detail`）。**例外**：文件上传见 `api/assets.ts`，因需要 `FormData` 而直接用 `fetch`（不要给它设 `Content-Type`，让浏览器带 boundary），但仍需按同样方式抛 `ApiError`。
- 每个领域一个 API 模块（`api/auth.ts`、`api/assets.ts`），组件不直接写请求；配套的查询键与缓存失效放在 `hooks/` 下（如 `useUploadAsset` 成功后失效 `['assets']`）。
- 画布/图层类交互使用 `konva` + `react-konva`；路由使用 `react-router-dom`，新页面需在 `src/App.tsx` 注册。
- 无障碍：图标等装饰性元素标注 `aria-hidden`。

## 测试与验证

- 后端测试通过 `httpx.ASGITransport` 直接驱动 `app`，**不启动真实服务器**；但 `test_health.py` 会断言数据库与对象存储连通性，`test_assets.py` 与 `conftest.py` 的 `bucket` fixture 会真实读写 MinIO——跑测试前需确保共享 PostgreSQL、MinIO 已启动（`docker compose -f ~/Desktop/postgres/docker-compose.yml up -d` 等），否则失败。
- **测试直连真实数据库与对象存储，没有隔离或 mock**：`conftest.py` 提供 `cleanup_users` 自动 fixture（每个用例结束后 `delete(User)`，靠级联清掉 assets），`credentials` fixture 生成随机用户名避免撞车。新增写库测试请沿用这些 fixture，不要自建清理逻辑；注意 MinIO 里的对象**不会**被数据库级联清掉，写对象存储的测试要自行考虑残留（现有上传测试会留下对象，属已知现象）。
- `pytest` 的 `asyncio_default_fixture_loop_scope` 与 `asyncio_default_test_loop_scope` 均为 `session`：数据库引擎在模块级创建，所有测试必须共享同一事件循环，否则连接跨循环复用会失败。**不要**改成 function 级。
- 前端暂无测试框架。改动前端后至少执行 `npm run build`（等价于类型检查）与 `npm run lint`。

## 已知坑

- **PostgreSQL 是 5433，不是默认的 5432**：默认端口已被其他项目的 postgres 占用，连接串照默认值写会连到别人的库上。MinIO 用默认的 9000/9001。Redis 也是默认的 6379，但**必须带库号**——写成 `redis://localhost:6379` 会落到 db 0，与占用该库的其他项目串数据。
- **MinIO 的桶由 `storage.ensure_bucket` 在应用启动时自动创建**（`main.py` 的 `lifespan`，`/api/health` 也会调用它）。若手工删掉了桶，重启后端或请求一次健康检查即可恢复，不必手动 `mc mb`。MinIO 侧的约定见 `~/Desktop/minio/README.md`。
- **签名 URL 里的 host 取自 `S3_ENDPOINT`**：当前是 `localhost:9000`，所以 URL 只能在本机浏览器打开；从局域网设备访问时需把 `S3_ENDPOINT` 改成 `http://192.168.1.100:9000` 并重启后端。
- `docs/` 不入库，不要假设存在；需要背景信息时先询问用户。
- 可选依赖 `cv`（rembg、onnxruntime、opencv-python-headless、rapidocr-onnxruntime）与 `agent`（langgraph、langchain）默认不装，本地需 `uv sync --all-extras`，Docker 构建已包含。rembg 模型权重挂在 `cv_models` 卷的 `/root/.u2net`。
- 前端静态挂载依赖 `frontend/dist` 存在，未构建时后端也能正常启动，属预期行为。
- 提交信息沿用中文 + Conventional Commits 前缀（如 `chore: 初始化项目骨架、本地基础设施`）。
