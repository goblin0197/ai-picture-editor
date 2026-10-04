# 账号业务逻辑：注册、登录校验、按 id 取用户。领域异常在此定义，由路由层翻译成 HTTP 状态码。
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.security import hash_password, verify_password


# 领域异常：用户名已被占用。由 register 抛出，routers/auth.py 翻译成 409 Conflict。
class UsernameTaken(Exception):
    pass


# 领域异常：用户名或密码错误。由 authenticate 抛出，routers/auth.py 翻译成 401。
class InvalidCredentials(Exception):
    pass


# 注册新用户。入参：session 会话；username 用户名；password 明文。出参：落库后的 User。
# 密码只存 bcrypt 哈希、绝不存明文；用户名重复时抛 UsernameTaken。
async def register(session: AsyncSession, username: str, password: str) -> User:
    user = User(username=username, password_hash=hash_password(password))
    session.add(user)
    try:
        await session.commit()
    # 唯一性靠数据库唯一约束在 commit 时兜底，而非「先查再插」。
    # 「先查后插」有 TOCTOU 竞态：两个并发注册可能都通过查询、再双双插入造成重复。
    # 交给约束后，冲突方 commit 抛 IntegrityError，在此捕获转成领域异常。
    except IntegrityError as exc:
        # 冲突后必须回滚，否则该 session 处于失效事务态，后续操作都会报错。
        await session.rollback()
        # raise ... from exc 保留异常链，便于调试时追溯到底层的约束冲突。
        raise UsernameTaken from exc
    return user


# 校验登录凭据。入参同 register；出参：校验通过的 User，失败一律抛 InvalidCredentials。
# 用户不存在与密码错误合并为同一异常，避免通过报错差异探测某用户名是否注册过。
async def authenticate(session: AsyncSession, username: str, password: str) -> User:
    user = await session.scalar(select(User).where(User.username == username))
    # user 为 None 或密码不匹配都走同一分支，对外表现一致。
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentials
    return user


# 按主键取用户，供 CurrentUser 依赖从会话令牌反解出用户时使用。
# 入参：user_id；出参：User 或 None（不存在）。
async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)
