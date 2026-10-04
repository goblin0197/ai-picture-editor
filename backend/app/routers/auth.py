# 账号认证路由：注册、登录、登出、查询当前用户。会话以 httponly Cookie 承载 JWT。
from fastapi import APIRouter, HTTPException, Response, status

from app.config import get_settings
from app.db import SessionDep
from app.deps import CurrentUser
from app.models import User
from app.schemas.auth import Credentials, UserOut
from app.security import SESSION_COOKIE, issue_token
from app.services import auth as auth_service

# 本模块路由前缀 /auth；经 main.py 套上 /api 后，对外路径为 /api/auth/*。
router = APIRouter(prefix="/auth", tags=["auth"])


# 私有辅助：签发会话并把令牌写进响应 Cookie，供 register/login 复用。
# 入参：response 用于写 Set-Cookie；user 当前用户。出参：UserOut（脱敏后的用户信息）。
def _start_session(response: Response, user: User) -> UserOut:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        # 令牌是用 user.id 签发的 JWT；下游 read_token 反解回 user_id。
        issue_token(user.id),
        # Cookie 存活时长与 JWT 有效期对齐（配置按小时计，这里换算成秒）。
        max_age=settings.jwt_ttl_hours * 3600,
        # httponly：JS 读不到该 Cookie，杜绝 XSS 窃取令牌；前端判断登录态改走 /auth/me。
        httponly=True,
        # samesite=lax：跨站请求不带该 Cookie 以缓解 CSRF，同源导航仍会带上。
        samesite="lax",
        # secure：仅生产要求 HTTPS 才下发，本地 http 开发才拿得到 Cookie。
        secure=settings.is_production,
        # path=/：整站生效；必须与 logout 里 delete_cookie 的 path 一致才能删掉。
        path="/",
    )
    # model_validate：从 ORM User 构造出参 UserOut，只暴露安全字段（不含密码哈希）。
    return UserOut.model_validate(user)


# 路由：POST /api/auth/register，成功状态码 201 Created。
@router.post("/register", status_code=status.HTTP_201_CREATED)
# 职责：注册新账号并立即登录（种下会话 Cookie）。
# 入参：credentials 用户名+密码；response 写 Cookie；session 会话。出参：UserOut。
async def register(credentials: Credentials, response: Response, session: SessionDep) -> UserOut:
    try:
        user = await auth_service.register(session, credentials.username, credentials.password)
    # 领域异常翻译成 HTTP：用户名被占用 → 409 Conflict。
    # from None 抑制异常链，不把内部 UsernameTaken 细节透传到响应里。
    except auth_service.UsernameTaken:
        raise HTTPException(status.HTTP_409_CONFLICT, "该用户名已被占用") from None
    # 注册成功即视为登录，复用 _start_session 下发会话。
    return _start_session(response, user)


# 路由：POST /api/auth/login，成功状态码 200（默认）。
@router.post("/login")
# 职责：校验用户名密码，通过则种下会话 Cookie。入参同 register；出参 UserOut。
async def login(credentials: Credentials, response: Response, session: SessionDep) -> UserOut:
    try:
        user = await auth_service.authenticate(session, credentials.username, credentials.password)
    # 凭据无效 → 401。用户名不存在与密码错误回同一消息，不暴露账号是否存在。
    except auth_service.InvalidCredentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误") from None
    return _start_session(response, user)


# 路由：POST /api/auth/logout，成功状态码 204 No Content（无响应体）。
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
# 职责：删除会话 Cookie 即登出；path 必须与种 Cookie 时一致否则删不掉。
# 无需校验登录态：本就是清凭据，未登录调用也无副作用。
async def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


# 路由：GET /api/auth/me，成功状态码 200。
@router.get("/me")
# 职责：返回当前登录用户。CurrentUser 依赖解析会话 Cookie，无效/未登录统一抛 401。
# 前端据此判断登录态：拿到 200 即已登录，收到 401 即视为未认证。
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
