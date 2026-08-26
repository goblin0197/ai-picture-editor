import os
import uuid

# 必须在任何 app 导入之前设置：环境变量优先级高于 .env。三条是结构性隔离的第一道防线：
# 1) 图片提供方固定为 mock —— 测试断言的是 mock 的确定性行为，不能因为 .env
#    切到真实模型就去调用外部服务（既慢又消耗额度）；下方 mock_provider fixture 再兜一层运行时保险。
# 2) 数据库指向独立测试库 —— 上游 0c99e7c 起 cleanup_users 只删 test_ 前缀账号，
#    但独立库仍是结构性兜底，不依赖清理逻辑本身永远正确。可用 TEST_DATABASE_URL 覆盖库地址。
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

from app import events  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import SessionFactory  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.providers import get_image_provider  # noqa: E402
from app.queue import close_queue  # noqa: E402
from app.storage import ensure_bucket  # noqa: E402

# 测试账号统一此前缀，清理时只删这些行，避免误清开发库里的真实用户
TEST_USER_PREFIX = "test_"
# 本地适配：上游开发用 redis db 0、测试挪 db 1；本机 db 0/1 已被其他项目占用，
# 本项目开发固定用 db 2，测试再让到 db 3（库号台账见 ~/Desktop/redis/README.md）
TEST_REDIS_DB = 3


@pytest.fixture(scope="session", autouse=True)
def bucket():
    ensure_bucket()


@pytest.fixture(scope="session", autouse=True)
def mock_provider():
    """测试一律走占位图实现，不受本机 IMAGE_PROVIDER 配置影响，也不产生调用费用。"""
    settings = get_settings()
    original, settings.image_provider = settings.image_provider, "mock"
    get_image_provider.cache_clear()
    yield
    settings.image_provider = original
    get_image_provider.cache_clear()


def _test_redis_url(url: str) -> str:
    head, _, tail = url.rpartition("/")
    return f"{head}/{TEST_REDIS_DB}" if tail.isdigit() else f"{url.rstrip('/')}/{TEST_REDIS_DB}"


@pytest.fixture(scope="session", autouse=True)
async def isolated_redis():
    """测试独占一个 Redis 库。开发中的 worker 只监听默认库，不会抢走测试投递的任务。"""
    settings = get_settings()
    original, settings.redis_url = settings.redis_url, _test_redis_url(settings.redis_url)
    events.redis_client.cache_clear()
    yield
    await close_queue()
    await events.redis_client().aclose()
    settings.redis_url = original
    events.redis_client.cache_clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _credentials() -> dict[str, str]:
    return {"username": f"{TEST_USER_PREFIX}{uuid.uuid4().hex[:10]}", "password": "secret123"}


@pytest.fixture
def credentials() -> dict[str, str]:
    return _credentials()


@pytest.fixture
def other_credentials() -> dict[str, str]:
    """第二个账号，用于验证跨用户访问被拒绝。"""
    return _credentials()


@pytest.fixture(autouse=True)
async def cleanup_users():
    yield
    async with SessionFactory() as session:
        await session.execute(delete(User).where(User.username.startswith(TEST_USER_PREFIX)))
        await session.commit()
