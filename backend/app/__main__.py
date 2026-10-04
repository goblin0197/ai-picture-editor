"""直接启动入口：在 backend/ 目录下执行 `uv run python -m app` 即可用配置里的端口起服务。

与 `uv run uvicorn app.main:app --reload --port 7302` 等价，区别只在两点：
端口不再写死在命令行（取 `Settings.api_port`，可用环境变量 `API_PORT` 覆盖），
且不带 `--reload`（开发改代码热重载仍建议用 uvicorn 命令）。

Python 约定：包目录下的 `__main__.py` 会在 `python -m <包名>` 时被执行，
`python -m app` 因此不需要额外入口脚本。
"""

import uvicorn

from app.config import get_settings

settings = get_settings()

# 第一个参数用「模块:变量」字符串而非直接传 app 对象：
# uvicorn 需要拿到可导入路径，才能在子进程里重新 import 应用（热重载与多 worker 都依赖这一点）。
uvicorn.run("app.main:app", host="127.0.0.1", port=settings.api_port)
