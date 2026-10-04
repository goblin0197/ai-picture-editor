# 账号表 ORM 模型：仅存用户名与密码哈希，其余通用列由 UUIDBase 提供
from sqlalchemy import String  # VARCHAR 列类型，带长度上限
from sqlalchemy.orm import Mapped, mapped_column  # 映射类型注解与列构造器

from app.models.base import UUIDBase  # 复用 UUID 主键 + created_at 基类


# 用户账号，对应数据库表 users，继承 UUIDBase 得到 id 与 created_at
class User(UUIDBase):
    __tablename__ = "users"  # 表名 users

    # 用户名：唯一（unique）且建索引（index），登录按它查找、不可重复
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    # 密码哈希：只存 bcrypt 哈希串（见 security.py），绝不存明文密码
    password_hash: Mapped[str] = mapped_column(String(128))
