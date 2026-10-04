# 数据库接入层：创建全局异步引擎、提供 ORM 声明式基类 Base，
# 并以 FastAPI 依赖（SessionDep）的形式向路由注入 AsyncSession。
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """所有 ORM 模型的声明式基类。models 下的表都继承它，Alembic 也据其元数据做迁移。"""

    pass


# 全局异步引擎：整个进程共用一个连接池。pool_pre_ping=True 会在借出连接前先探活，
# 避免拿到被数据库/中间件断开的死连接（长时间空闲后常见）。
engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
# 会话工厂。expire_on_commit=False：commit 后不使已加载对象的属性过期，
# 这样响应序列化时再读字段不会触发「过期→重新查询」，也避免脱离会话后访问报错。
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI 依赖：每个请求产出一个会话，请求结束由 async with 负责关闭/归还连接。

    用 yield 而非 return，使其成为「生成器型依赖」——yield 之前是进入、之后是收尾。
    """
    async with SessionFactory() as session:
        yield session


# 类型别名 + Depends：路由参数标注为 SessionDep 即可自动注入会话，
# 无需各处手写 Depends(get_session)，也统一了「不要自建 session」的约定。
SessionDep = Annotated[AsyncSession, Depends(get_session)]
