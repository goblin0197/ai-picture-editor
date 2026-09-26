# AGENTS.md

本文件为 ZCode 等编码代理提供本仓库的上下文与硬性约定。**所有代码注释、提交信息、UI 文案一律使用中文。**

## 项目定位

AI 修图智能体（compose 项目名 `ai-retouch-agent`）：一句话生成商品图，或上传图片后继续编辑，自动串联抠图、换背景、局部修改与多尺寸导出。

当前进度：本地基础设施、健康检查、ARQ 投递链路、前端外壳、**账号注册登录**、**素材上传与对象存储**、**落地页与视觉规范**、**文生图链路与候选选图**已就绪；编辑、批量、导出尚未实现，`/editor`、`/batch` 等仍为占位页并标注了计划中的开发步骤编号（S4、S11 等）。

## 目录结构

| 路径 | 说明 |
| --- | --- |
| `backend/app/main.py` | FastAPI 入口，`lifespan` 中建桶，挂载 `/api` 路由与前端静态产物 |
| `backend/app/config.py` | `Settings`（pydantic-settings），从**仓库根目录** `.env` 读取 |
| `backend/app/db.py` | 异步引擎、`Base`、`SessionDep` 依赖 |
| `backend/app/deps.py` | `CurrentUser` 依赖，从会话 Cookie 解出当前用户 |
| `backend/app/security.py` | 密码哈希（bcrypt）与 JWT 会话令牌签发/解析 |
| `backend/app/storage.py` | 对象存储封装（boto3/S3），`ensure_bucket` 与签名 URL |
| `backend/app/events.py` | Redis 发布订阅，向 SSE 推送任务进度 |
| `backend/app/queue.py` | ARQ 投递入口，`enqueue` 以 run id 作为 job id 保证幂等 |
| `backend/app/ratios.py` | 输出比例枚举与像素尺寸（与交付尺寸对齐） |
| `backend/app/providers/` | 图像模型适配层：`base.py` 定义 Protocol，`mock`/`dashscope` 各一份实现，另有本地新增的 `openai_images.py` |
| `backend/app/routers/` | 路由模块，每个模块自带 `prefix` 与 `tags`；`events.py` 是 SSE，单独挂载 |
| `backend/app/services/` | 业务逻辑（`auth` 账号、`assets` 素材、`images` 图片校验、`runs` 任务状态、`generation` 生成编排） |
| `backend/app/schemas/` | Pydantic 出参模型，`XxxOut.of(orm_obj)` 从 ORM 对象构造 |
| `backend/app/tasks/` | ARQ 异步任务，`__init__.py` 的 `TASKS` 列表即 worker 注册表 |
| `backend/app/models/` | SQLAlchemy ORM 模型，`base.py` 提供 `UUIDBase`、`TIMESTAMPTZ` 与 `enum_column` |
| `backend/migrations/versions/` | Alembic 迁移脚本，文件名 `日期_序号_描述.py` |
| `backend/tests/` | pytest 测试（`asyncio_mode = "auto"`，直接用顶层 `async def`） |
| `backend/scripts/` | 手工自检脚本，如 `e2e_generation.py` 跑通整条生成链路 |
| `frontend/src/api/` | `client.ts` 是通用请求出口；`auth.ts`/`assets.ts`/`runs.ts` 是分领域封装 |
| `frontend/src/hooks/` | React Query 封装（`useAuth`、`useAssets`、`useRun`），含查询键与失效策略；`useRun` 还负责订阅 SSE |
| `frontend/src/components/` | 可复用组件（`BrandMark`、`AssetCard`、`ImageDropzone`、`GenerateForm`） |
| `frontend/src/components/landing/` | 落地页分区组件，`previews.tsx` 用纯样式拼界面示意图（无图片资源） |
| `frontend/src/layouts/` | `RequireAuth`（登录守卫）、`WorkbenchLayout`（工作台外壳） |
| `frontend/src/lib/` | 无 UI 依赖的工具（`format`、`promptDraft` 草稿读写） |
| `frontend/src/index.css` | Tailwind v4 `@theme` 设计令牌 + `@utility` 自定义工具类（**无 tailwind.config.js**） |
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
uv run arq app.worker.WorkerSettings      # worker，生成类接口必须它在线才跑得动
uv run pytest                             # 测试
uv run ruff check .                       # lint（line-length 100，规则 E/F/I/UP/B）
uv run alembic revision --autogenerate -m "描述"
uv run alembic upgrade head
uv run python scripts/e2e_generation.py   # 文生图链路端到端自检（需后端与 worker 都在跑）
```

**生成类功能需要三个进程同时在跑**：uvicorn、arq worker、以及基础设施。只起后端时接口能返回 202，但任务会一直停在 `queued`——因为没人消费队列。

前端（在 `frontend/` 下执行，需 Node 22+）：

```bash
npm ci
npm run dev      # → http://localhost:7301
npm run build    # tsc -b && vite build，类型错误会中断构建
npm run lint     # oxlint
```

## 架构边界与硬性约定

**前后端始终同源。** 生产环境由 FastAPI 以 `StaticFiles` 在 `/` 托管 `frontend/dist`；开发环境由 Vite 代理 `/api` 与 `/events` 到 7302。因此前端必须使用相对路径（`/api/...`、`/events`），**不要硬编码绝对地址或引入 CORS 配置**——httpOnly Cookie 与 SSE 正是依赖同源才能零配置工作。

**API 前缀只在 `main.py` 集中声明。** `main.py` 用 `APIRouter(prefix="/api")` 聚合各 router，路由模块自身只写业务前缀（如 `/health`），重复添加 `/api` 会导致 404。接口文档在 `/api/docs`。**唯一例外是 SSE**：`events.router` 挂在 `/events`（不在 `/api` 下），便于反向代理单独关闭缓冲；前端 `/events` 也已在 `vite.config.ts` 里代理到 7302，两边要同步改。

**长任务走「建记录 → 投递 → worker 消费」三步，不要同步跑。** 参考 `services/runs.py` + `queue.py` + `tasks/`：接口建 `ToolRun` 并返回 202，用 `enqueue` 投递，worker 侧的 `tasks/generate.py` 负责执行。三条硬约束：

1. **任务必须以 run id 作为 job id**（`queue.enqueue` 里 `_job_id=str(run_id)`），重复投递才不会二次执行。
2. **worker 消费前先查状态，终态直接返回**（`tasks/generate.py` 的 `run.status.is_terminal` 守卫），防队列重投与 worker 重启后的重复消费。
3. **任何异常都必须落终态**。否则订阅 SSE 的客户端会一直空等——`tasks/generate.py` 里那个兜底 `except Exception` 就是为了这个，不要删。

**进度推送经 Redis 发布订阅，不落库轮询。** worker 侧 `services/runs.py` 每次状态变更后 `events.publish`，接口侧 `routers/events.py` 订阅同一频道转成 SSE。注意它**先订阅再读快照**的顺序：反过来的话，任务在两步之间结束会让连接一直空等。任务终态时服务端主动断开（客户端重连会先收到快照）。

**新增异步任务必须注册。** 在 `app/tasks/` 写函数后，追加到 `app/tasks/__init__.py` 的 `TASKS` 列表，否则 worker 不会加载。任务签名固定为 `async def fn(ctx: dict)`。

**新增模型提供方在 `providers/__init__.py` 登记。** 实现 `providers/base.py` 的 `ImageProvider` Protocol（`generate` 返回图片字节列表，失败抛 `ProviderError`；`on_progress` 回调用于上报进度），然后在 `get_image_provider()` 的分支里加上。调用方只认 Protocol，新增平台不改调用方。

**新增 ORM 模型必须在 `app/models/__init__.py` 导出**，否则 Alembic autogenerate 发现不到该表。

**时间列一律用 `models/base.py` 的 `TIMESTAMPTZ`**（`DateTime(timezone=True)`），全库统一带时区存储，避免跨时区读写歧义。**枚举列用 `enum_column()`**——它以 VARCHAR 存枚举的 value 而非 PostgreSQL 原生枚举，增删取值不需要 `ALTER TYPE`。

**Alembic 连接串来自应用配置**（`migrations/env.py` 调用 `get_settings().database_url`），`alembic.ini` 中不配置 `sqlalchemy.url`，不要在那里填写连接信息。

**配置来源统一。** `Settings` 读取仓库根目录的 `.env`（`.env.example` 是模板，已被 `.gitignore` 忽略实际 `.env`），字段名小写、环境变量名大写无前缀（`IMAGE_PROVIDER` → `image_provider`）。`get_settings()` 带 `lru_cache`，测试中如需改配置要清缓存。

**数据库会话通过 `SessionDep` 注入**（`app/db.py` 的 `Annotated[AsyncSession, Depends(get_session)]`），不要自行创建 session。

**认证依赖 `CurrentUser`。** 需要登录的接口注入 `app/deps.py` 的 `CurrentUser`（`Annotated[User, Depends(...)]`），它从 `session` Cookie 解析 JWT；无效一律按 401 处理。会话 Cookie 是 `HttpOnly; SameSite=lax`，前端拿不到也不该去读它——判断登录态走 `useAuth` 的 `useCurrentUser`（未登录时后端返回 401，前端据此视为未认证）。

**素材接口一律按 `user_id` 过滤。** 查询素材必须用 `services/assets.get_for_user` 这类「主键 + user_id 联合条件」的方式，返回 404 而非 403，避免泄露他人资源是否存在；对象存储的 key 也以 `users/<user_id>/` 为前缀隔离。

**对象存储经 `app/storage.py` 访问，不要直接调 boto3。** 该模块用 `lru_cache` 复用客户端，并把同步调用包在 `asyncio.to_thread` 里；桶在 `main.py` 的 `lifespan` 中自动创建（`ensure_bucket`），无需手工建桶。对外一律用签名 URL（`signed_url`），不回传原始对象直链。

**图片校验在 `services/images.py` 的 `probe()` 内集中处理**（大小、格式、最小边长、像素总量），格式以**实际解码结果**为准而非文件扩展名或客户端 Content-Type。新增图片入口请复用该函数，不要在各 router 里重复校验。

**图像提供方默认 `mock`**，用提示词哈希决定构图生成占位图（同一提示词结果稳定）、不产生调用费用；切到 `dashscope` 才走真实模型（`qwen-image-3.0-pro` / `qwen-image-edit-max` / `qwen-plus`，走异步提交+轮询，参考图以 base64 内联）。**开发与测试不要擅自改动该开关或消耗真实额度**——现有测试全部跑在 mock 上。

**本仓库有一处上游没有的本地扩展：`openai` 提供方**（`app/providers/openai_images.py`）。它是为了对接本机的 OpenAI 兼容网关（`DASHSCOPE_BASE_URL` 指向 `192.168.1.100:8081/v1`）而新增的，对应 `IMAGE_PROVIDER=openai`。三点与上游不同，改动上游文件时注意保留：`providers/__init__.py` 里多一个 `if name == "openai"` 分支；该提供方复用 `dashscope_*` 配置而非新增一组；它不支持参考图（`references` 非空时直接抛 `ProviderError`）。协议差异：走 `/v1/images/generations` 一次 POST 同步返回（不像 dashscope 要轮询任务），尺寸是 `WIDTHxHEIGHT`（用 `x`），响应给 `data[].url` 或 `data[].b64_json`（两种都处理）。

**该网关有三个实测得出的脾气**，改这个适配器前务必知道：① **对模型有分类**——`agnes-image-*` 与 `grok-4.7` 不属于图片模型、报 `images endpoint requires an image model`，实测可用的是 `gpt-image-2`；② **忽略 `n` 参数**，无论给几都只回 1 张，所以适配器首轮按 count 请求、不足时并行补足（串行会把耗时乘上张数，`count=2` 实测约 90 秒）；③ 会把请求尺寸吸附到 16 的倍数（请求 1080×1080 实际返回 1088×1088），落库的是**实际解码尺寸**，与 `ratios.py` 声明的交付尺寸不严格相等。

**关于 agnes 模型（2026-09-26 更新，已可用）**：原先 `agnes-image-*` 被网关拦在图片端点外，报 `images endpoint requires an image model`。根因是 sub2api 网关（`~/Desktop/sub2api`）的白名单里只有 `gpt-image-` 与 `grok-imagine-image` 两个前缀——**上游本身是支持 agnes 走图片端点的**（直连上游测试：`/v1/chat/completions` 返回「Model ... is an image model. Use /v1/images/generations」，而 `/v1/images/generations` 用 agnes 能正常出图）。用户已在 sub2api 侧新增 `isAgnesCompatibleImageModel`（`backend/internal/service/openai_images.go`，接入 `validateCompatibleImagesModel`）并重建容器，现在 agnes 可用。**这是 sub2api 的改动，不在本仓库**。

**agnes 与 gpt-image-2 的行为差异**（适配器已同时兼容两者）：agnes **拒绝 `n>1`**（直接报 `n must be 1`，不是像 gpt-image-2 那样静默只回 1 张），所以 `_collect` 先试 count、被拒就退回单张模式；agnes 更快（单张约 10 秒、4 张约 26 秒，而 gpt-image-2 单张约 36 秒、4 张约 111 秒）；agnes 返回 1024×1024（不带 16 倍数吸附）。上游对 agnes 的 size 接受 `1K/2K/3K/4K` 或 `WIDTHxHEIGHT`。

## 编码规范

后端：

- Ruff 负责格式化与 lint，提交前跑 `uv run ruff check .`。
- 已知必须保留的例外用带原因的 `# noqa: <rule> - 中文原因`，参见 `app/routers/health.py` 中的 `BLE001`。
- 类型注解完整；`Settings` 类只声明带默认值的字段。

前端：

- `tsconfig.app.json` 开启了 `verbatimModuleSyntax`（类型导入必须写 `import type`）、`noUnusedLocals`、`noUnusedParameters`、`erasableSyntaxOnly`，构建即类型检查。
- 路径别名 `@` → `frontend/src` 在 `vite.config.ts` 与 `tsconfig.app.json` **两处各配一份**，改动时必须同步。
- 样式一律走语义令牌，不要写字面值。颜色用 `text-ink`/`bg-paper`/`border-line`/`bg-brand-soft`/`text-muted`/`text-faint`/`text-danger` 等，圆角用 `rounded-card`(18px)/`rounded-control`(12px)/`rounded-panel`(26px)，阴影用 `shadow-card`/`shadow-control`/`shadow-lift`/`shadow-panel`。字号等无令牌的可用行内写法（如 `text-[15px]`）。**已知遗留**：`WorkbenchLayout`、`AssetCard`、`ImageDropzone` 里还有 `rounded-[12px]`/`rounded-[18px]` 字面值，它们与 `rounded-control`/`rounded-card` 等价，改到时顺手替换即可。
- 自定义工具类定义在 `index.css` 的 `@utility` 中（`bg-glow` 顶部光晕、`bg-grid` 网格底纹），不要为一次性样式另建 CSS 文件。
- 动效统一用 `animate-rise` 入场（配 `style={{ animationDelay }}` 做错峰），并依赖 `index.css` 中已有的 `prefers-reduced-motion` 全局降级——新增动画无需自己处理该媒体查询。
- 服务端状态用 `@tanstack/react-query`，请求统一走 `@/api/client` 的 `api`；错误已归一化为 `ApiError`（携带 `status` 与后端 `detail`）。**例外**：文件上传见 `api/assets.ts`，因需要 `FormData` 而直接用 `fetch`（不要给它设 `Content-Type`，让浏览器带 boundary），但仍需按同样方式抛 `ApiError`。
- 每个领域一个 API 模块（`api/auth.ts`、`api/assets.ts`、`api/runs.ts`），组件不直接写请求；配套的查询键与缓存失效放在 `hooks/` 下（如 `useUploadAsset` 成功后失效 `['assets']`）。
- **实时进度用 `EventSource` 直连 `/events/runs/<id>`，不要塞进 react-query**。`hooks/useRun.ts` 是范例：SSE 提供实时状态，react-query 的快照接口提供候选图与刷新恢复能力，两者合并后按「`live.id === runId`」判定可用性——否则切换任务时旧连接的残留帧会串到新任务上。连接出错时回退去刷新快照，界面不会停在过期进度上。
- 提交长任务后跳转到结果页（`/candidates/:runId`），不要原地等结果——任务由 worker 异步执行，页面刷新后靠快照接口恢复。
- 页面组件只做组装：`LandingPage` 仅组合 `components/landing/*`，状态与交互下沉到分区组件（如 `LandingHero` 自己持有输入状态）。新增落地页区块放 `components/landing/`。
- 品牌标识统一用 `components/BrandMark.tsx`（`size="sm" | "md"`，可选 `children` 放文字），落地页、登录页、工作台三处共用，不要再手写 logo。
- `sessionStorage`/`localStorage` 访问一律用 `try/catch` 包裹（见 `lib/promptDraft.ts`）——隐私模式下会直接抛异常，不能让草稿读写中断主流程。
- 画布/图层类交互使用 `konva` + `react-konva`；路由使用 `react-router-dom`，新页面需在 `src/App.tsx` 注册。
- 无障碍：图标等装饰性元素标注 `aria-hidden`；纯装饰性的界面示意图整个容器加 `aria-hidden`（见 `previews.tsx`）。

## 测试与验证

- 后端测试通过 `httpx.ASGITransport` 直接驱动 `app`，**不启动真实服务器**；但 `test_health.py` 会断言数据库与对象存储连通性，`test_assets.py` 与 `conftest.py` 的 `bucket` fixture 会真实读写 MinIO，`test_generation.py` 会真的调 worker 任务函数并在 SSE 上收帧——跑测试前需确保共享 PostgreSQL、MinIO、Redis 都已启动（`docker compose -f ~/Desktop/postgres/docker-compose.yml up -d` 等），否则失败。
- **测试连的是真实服务的独立库与独立桶，不使用 mock 数据库**（见下方三条隔离设置）：`cleanup_users` 自动 fixture 在每个用例结束后 `delete(User)`，靠级联清掉 assets 与 tool_runs；`credentials` fixture 生成随机用户名避免撞车。新增写库测试请沿用这些 fixture，不要自建清理逻辑。
- **`conftest.py` 顶部强制三条隔离设置**（环境变量优先级高于 `.env`，必须在 `app` 导入前设置）：
  1. `IMAGE_PROVIDER=mock` —— 否则 `.env` 切到真实模型后，测试会真的调用外部服务（实测耗时 9 秒 → 134 秒、消耗真额度），且断言 mock 特有尺寸/数量的用例会失败。
  2. `DATABASE_URL` → **独立测试库 `retouch_test`** —— `cleanup_users` 执行的是无 WHERE 条件的 `delete(User)`（上游遗留写法），跑在开发库上会把真实账号连级联数据一起删光。可用 `TEST_DATABASE_URL` 环境变量覆盖库地址。
  3. `S3_BUCKET=retouch-test` —— MinIO 对象不受数据库级联删除影响，用独立桶避免测试残留污染开发桶。

  **这三点不要删**。测试库结构用 `DATABASE_URL=...retouch_test uv run alembic upgrade head` 初始化（或在测试库空时先跑一次迁移）。
- **`cleanup_users` 删的是整张表，会连真实账号一起清掉**：`delete(User)` 没有 WHERE 条件。上游在很后面的提交里才把它改成只删测试账号。**隔离靠上面的独立测试库**，不要再依赖「跑测试前先确认没重要数据」这种人肉措施；跑完测试若发现开发桶有多余对象（各以 `users/<空闲 UUID>/` 为前缀），需手工清理。
- **测试会真的往 Redis 队列投递任务**（`POST /api/generations` 内部调 `enqueue`），而 `test_generation.py` 又直接调 `generate_images` 同步执行。跑完一轮测试 Redis 里会留下若干 `arq:result:*` 键（TTL 约 1 小时自清）；此时启动 worker 会把它们再捡一遍，但 `is_terminal` 守卫让它们瞬间返回——这是预期行为，不是异常。
- `pytest` 的 `asyncio_default_fixture_loop_scope` 与 `asyncio_default_test_loop_scope` 均为 `session`：数据库引擎在模块级创建，所有测试必须共享同一事件循环，否则连接跨循环复用会失败。**不要**改成 function 级。
- 前端暂无测试框架。改动前端后至少执行 `npm run build`（等价于类型检查）与 `npm run lint`。

## 已知坑

- **PostgreSQL 是 5433，不是默认的 5432**：默认端口已被其他项目的 postgres 占用，连接串照默认值写会连到别人的库上。MinIO 用默认的 9000/9001。Redis 也是默认的 6379，但**必须带库号**——写成 `redis://localhost:6379` 会落到 db 0，与占用该库的其他项目串数据。
- **当前 `uv run ruff check .` 会报 2 个 E501 行超长错误**，都在 `backend/tests/test_generation.py` 那两行硬编码的 `test_intruder` 注册上（第 95、122 行）。这是上游遗留问题，它在很后面的提交里才换成 `other_credentials` fixture 一并修掉。**本地不要擅自修**，否则与上游产生差异、影响对照学习。
- **改了数据库结构后要重启后端**：asyncpg 会缓存预编译语句计划，运行期间执行 `ALTER TABLE`（如 `timestamptz` 迁移）会让缓存计划失效，报 `InvalidCachedStatementError`。SQLAlchemy 的 asyncpg 方言会自动清缓存、下一次请求即恢复；但更稳妥的做法是「先停服务 → 跑迁移 → 再启动」。
- **MinIO 的桶由 `storage.ensure_bucket` 在应用启动时自动创建**（`main.py` 的 `lifespan`，`/api/health` 也会调用它）。若手工删掉了桶，重启后端或请求一次健康检查即可恢复，不必手动 `mc mb`。MinIO 侧的约定见 `~/Desktop/minio/README.md`。
- **签名 URL 里的 host 取自 `S3_ENDPOINT`，因此它决定了图片能否被打开**：当前本机配置是 `http://192.168.1.100:9000`（局域网 IP），所以本机与局域网设备都能打开签名 URL。**不要改回 `localhost`**——签名参数含 `X-Amz-SignedHeaders=host`，host 参与签名计算，把 URL 里的地址手工换成别的（或反向）都会得到 `SignatureDoesNotMatch`，必须由后端用正确的 host 重新签发。若在无局域网的纯单机环境使用，改回 `localhost` 也可以，但改完要重启后端与 worker。
- **外部模型返回的图片链接 24 小时过期**，`services/generation.py` 会立即下载并转存到自有存储后才落库。新增对接外部模型时务必照此处理，不要把外部临时链接直接存进 `result`。
- `docs/` 不入库，不要假设存在；需要背景信息时先询问用户。
- 可选依赖 `cv`（rembg、onnxruntime、opencv-python-headless、rapidocr-onnxruntime）与 `agent`（langgraph、langchain）默认不装，本地需 `uv sync --all-extras`，Docker 构建已包含。rembg 模型权重挂在 `cv_models` 卷的 `/root/.u2net`。
- 前端静态挂载依赖 `frontend/dist` 存在，未构建时后端也能正常启动，属预期行为。
- 提交信息沿用中文 + Conventional Commits 前缀（如 `chore: 初始化项目骨架、本地基础设施`）。
