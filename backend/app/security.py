# 安全工具：用户口令的哈希与校验（bcrypt），以及会话令牌 JWT 的签发与解析。
# 会话令牌最终放进 httpOnly Cookie，deps.current_user 会调用 read_token 还原用户身份。
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import get_settings

SESSION_COOKIE = "session"  # 存放会话 JWT 的 Cookie 名，前后端与依赖注入共用这一常量
_ALGORITHM = "HS256"  # JWT 签名算法：HMAC-SHA256，对称密钥（要求密钥不短于 32 字节）


def hash_password(plain: str) -> str:
    """把明文口令哈希成可入库的字符串。"""
    # gensalt() 每次生成随机盐并内嵌进结果，故同一口令每次哈希值都不同；
    # bcrypt 接口收发 bytes，这里 encode 传入、decode 成 str 落库。
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文口令与库中哈希是否匹配，返回布尔值。"""
    # checkpw 会从 hashed 中解出当初的盐再比对，并做恒定时间比较以抵御时序攻击。
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def issue_token(user_id: uuid.UUID) -> str:
    """为指定用户签发会话令牌（JWT 字符串）。"""
    settings = get_settings()
    payload = {
        "sub": str(user_id),  # subject：令牌主体，这里存用户 ID（UUID 转字符串）
        # exp：过期时间，取带时区的 UTC「现在 + 配置小时数」；PyJWT 解码时会自动校验它。
        "exp": datetime.now(UTC) + timedelta(hours=settings.jwt_ttl_hours),
    }
    # 用配置里的密钥与 HS256 对称签名，得到最终令牌字符串。
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def read_token(token: str) -> uuid.UUID | None:
    """解析会话令牌，任何无效情形统一返回 None 交由调用方处理为未认证。"""
    try:
        # 验签 + 校验 exp（过期会抛异常）；algorithms 白名单写死，防「alg=none」等降级攻击。
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[_ALGORITHM])
        return uuid.UUID(payload["sub"])  # 取回主体并还原成 UUID
    except (jwt.InvalidTokenError, KeyError, ValueError):
        # 三类失败合并处理：InvalidTokenError=签名错/过期/格式坏，
        # KeyError=载荷缺 sub，ValueError=sub 不是合法 UUID。任一都视作无效令牌。
        return None
