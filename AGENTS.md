# AGENTS.md

本文件为 ZCode 等编码代理提供本仓库的上下文与硬性约定。**所有代码注释、提交信息、UI 文案一律使用中文。**

## 项目定位

AI 修图智能体（compose 项目名 `ai-retouch-agent`）：一句话生成商品图，或上传图片后继续编辑，自动串联抠图、换背景、局部修改与多尺寸导出。

当前为**骨架阶段**：本地基础设施、后端健康检查、ARQ 投递链路、前端外壳已就绪；业务功能（生成、编辑、批量、导出）尚未实现，占位页标注了计划中的开发步骤编号。

## 目录结构

| 路径 | 说明 |
| --- | --- |
| `backend/app/main.py` | FastAPI 入口，挂载 `/api` 路由与前端静态产物 |
| `backend/app/config.py` | `Settings`（pydantic-settings），从**仓库根目录** `.env` 读取 |
| `backend/app/db.py` | 异步引擎、`Base`、`SessionDep` 依赖 |
| `backend/app/routers/` | 路由模块，每个模块自带 `prefix` 与 `tags` |
| `backend/app/tasks/` | ARQ 异步任务，`__init__.py` 的 `TASKS` 列表即 worker 注册表 |
| `backend/app/models/` | SQLAlchemy ORM 模型（目前为空包） |
| `backend/migrations/` | Alembic 迁移，`versions/` 目录尚无内容 |
| `backend/tests/` | pytest 测试（`asyncio_mode = "auto"`，直接用顶层 `async def`） |
| `frontend/src/api/client.ts` | 唯一请求出口，基于 `fetch` 封装 `api.get/post/patch/delete` |
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
- 服务端状态用 `@tanstack/react-query`，请求统一走 `@/api/client` 的 `api`；错误已归一化为 `ApiError`（携带 `status` 与后端 `detail`）。
- 画布/图层类交互使用 `konva` + `react-konva`；路由使用 `react-router-dom`，新页面需在 `src/App.tsx` 注册。
- 无障碍：图标等装饰性元素标注 `aria-hidden`。

## 测试与验证

- 后端测试通过 `httpx.ASGITransport` 直接驱动 `app`，**不启动真实服务器**；但 `test_health.py` 会断言数据库连通性，跑测试前需确保共享 PostgreSQL 已启动（`docker compose -f ~/Desktop/postgres/docker-compose.yml up -d`），否则该用例失败。
- 目前没有测试数据库隔离或 mock，测试直连配置中的库——新增涉及写库的测试时需自行处理数据清理。
- 前端暂无测试框架。改动前端后至少执行 `npm run build`（等价于类型检查）与 `npm run lint`。

## 已知坑

- **PostgreSQL 是 5433，不是默认的 5432**：默认端口已被其他项目的 postgres 占用，连接串照默认值写会连到别人的库上。MinIO 用默认的 9000/9001。Redis 也是默认的 6379，但**必须带库号**——写成 `redis://localhost:6379` 会落到 db 0，与占用该库的其他项目串数据。
- **MinIO 的桶不会自动创建**（没有 MySQL 建库、PostgreSQL `POSTGRES_DB` 那样的开关），需 `docker exec minio mc mb --ignore-existing local/retouch`；详见 `~/Desktop/minio/README.md`。
- `docs/` 不入库，不要假设存在；需要背景信息时先询问用户。
- 可选依赖 `cv`（rembg、onnxruntime、opencv-python-headless、rapidocr-onnxruntime）与 `agent`（langgraph、langchain）默认不装，本地需 `uv sync --all-extras`，Docker 构建已包含。rembg 模型权重挂在 `cv_models` 卷的 `/root/.u2net`。
- 前端静态挂载依赖 `frontend/dist` 存在，未构建时后端也能正常启动，属预期行为。
- 提交信息沿用中文 + Conventional Commits 前缀（如 `chore: 初始化项目骨架、本地基础设施`）。
