import os
import uuid

# 必须在任何 app 导入之前设置：环境变量优先级高于 .env。三条都关乎数据安全：
# 1) 图片提供方固定为 mock —— 测试断言的是 mock 的确定性行为，不能因为 .env
#    切到真实模型就去调用外部服务（既慢又消耗额度）。
# 2) 数据库指向独立测试库 —— cleanup_users 会清空整张 users 表，跑在开发库上
#    会把真实账号一并删除（靠级联还会带走素材与任务记录）。
# 3) 对象存储用独立桶 —— MinIO 对象不受数据库级联删除影响，测试残留会污染开发桶。
os.environ["IMAGE_PROVIDER"] = "mock"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5433/retouch_test",
)
os.environ["S3_BUCKET"] = "retouch-test"

import httpx  # noqa: E402
import pytest  # noqa: E402
from httpx import ASGITransport  # noqa: E402
from sqlalchemy import delete  # noqa: E402

from app.db import SessionFactory  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.storage import ensure_bucket  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def bucket():
    ensure_bucket()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def credentials() -> dict[str, str]:
    return {"username": f"u{uuid.uuid4().hex[:10]}", "password": "secret123"}


@pytest.fixture(autouse=True)
async def cleanup_users():
    yield
    async with SessionFactory() as session:
        await session.execute(delete(User))
        await session.commit()
