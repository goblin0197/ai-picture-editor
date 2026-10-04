# 认证依赖：从 httpOnly 的会话 Cookie 中解出当前登录用户，供需要鉴权的接口注入。
# 无 Cookie、令牌无效、用户不存在这三种情况一律按 401 处理，不向客户端区分具体原因。
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status

from app.db import SessionDep
from app.models import User
from app.security import SESSION_COOKIE, read_token
from app.services import auth as auth_service

# 预先构造的 401 异常，三处失败分支复用同一个实例，对外只给一句笼统提示；
# 故意不区分「没登录 / 令牌坏了 / 用户已删」，避免被用来探测账号是否存在。
_UNAUTHENTICATED = HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录或会话已过期")


async def current_user(
    session: SessionDep,  # 数据库会话，由 SessionDep 依赖自动注入
    # 从名为 SESSION_COOKIE 的 Cookie 读取令牌；缺省 None 表示请求根本没带这个 Cookie。
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User:
    """解析会话 Cookie，返回当前登录用户；任一环节失败都抛统一的 401。"""
    if token is None:  # 请求未携带会话 Cookie，视为未登录
        raise _UNAUTHENTICATED

    user_id = read_token(token)  # 校验并解出令牌里的用户 ID（失效/伪造会得到 None）
    if user_id is None:
        raise _UNAUTHENTICATED

    # 令牌本身合法，但对应用户可能已被删除；查不到同样按未认证处理。
    user = await auth_service.get_by_id(session, user_id)
    if user is None:
        raise _UNAUTHENTICATED
    return user


# 类型别名 + Depends：需要登录的接口把参数标注为 CurrentUser 即可拿到 User 对象，
# 未通过认证时依赖会先抛 401，业务代码无需再自行判空。
CurrentUser = Annotated[User, Depends(current_user)]
