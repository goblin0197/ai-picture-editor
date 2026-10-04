# 所有 ORM 模型共享的基类与列类型工具，集中定义主键、时间戳与枚举列约定
import enum  # 标准库枚举，业务枚举（如 AssetKind）均继承 enum.StrEnum
import uuid  # 主键使用 UUID，应用侧生成而非数据库自增
from datetime import datetime  # created_at 等时间列的 Python 类型

from sqlalchemy import DateTime, Enum, func  # 时间列/枚举列类型与 SQL 函数
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # PG 原生 UUID 列类型
from sqlalchemy.orm import Mapped, mapped_column  # 映射类型注解与列构造器

from app.db import Base  # 声明式基类，所有表模型的根

# 枚举列以 VARCHAR 存储时的长度上限（字符），需能容纳最长的枚举 value
ENUM_LENGTH = 16

# 全库时间统一带时区存储，避免跨时区读写产生歧义
TIMESTAMPTZ = DateTime(timezone=True)


# 工厂函数：为某个枚举类生成对应的 SQLAlchemy 列类型
def enum_column(enum_cls: type[enum.Enum]) -> Enum:
    """以 VARCHAR 存枚举值本身，读取时还原为枚举成员。

    不使用 PostgreSQL 原生枚举，增删取值无需 ALTER TYPE。
    """
    # 返回值仍是 Enum 类型，但底层落地为 VARCHAR 而非 PG 原生枚举
    return Enum(
        enum_cls,
        native_enum=False,  # 不用 PG 原生 ENUM，改以 VARCHAR 存储
        create_constraint=False,  # 不建 CHECK 约束，增删取值无需 ALTER
        # 存入的是 member.value 而非成员名，读取时自动还原为枚举成员
        values_callable=lambda cls: [member.value for member in cls],
        length=ENUM_LENGTH,  # VARCHAR 长度上限
    )


# 抽象基类：统一「UUID 主键 + 创建时间」两列，供各业务表继承
class UUIDBase(Base):
    __abstract__ = True  # 抽象类，自身不建表，只把列定义传给子类

    # 主键 id：应用侧用 uuid4 生成默认值，无需依赖数据库序列
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # created_at：插入时由数据库以 now() 填充（server_default），带时区
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())
