"""编辑会话表 ORM 模型：编辑页左栏的一条对话 + 其图片墙关联表。"""

import uuid  # 外键的 UUID 类型
from datetime import datetime  # updated_at 的类型

from sqlalchemy import ForeignKey, String, func  # 外键、VARCHAR、数据库当前时间
from sqlalchemy.dialects.postgresql import JSONB  # JSONB 列，存画布文档
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # PG 原生 UUID 列类型
from sqlalchemy.orm import Mapped, mapped_column  # 映射类型注解与列构造器

from app.db import Base  # 声明式基类（SessionAsset 不需要自增主键，用普通 Base）
from app.models.base import TIMESTAMPTZ, UUIDBase  # 带时区时间列与 UUID 主键基类


class EditSession(UUIDBase):
    """编辑页左栏的一条对话。document 是该会话当前画布的权威描述。

    「权威描述」的含义：前端画布渲染、后续工具（抠图/换背景…）的输入都以
    document 为准，不存在第二份画布状态；每步操作落历史（EditHistory）并更新它。
    """

    __tablename__ = "edit_sessions"

    # 归属用户外键：删用户级联删会话；建索引便于按用户列会话
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(80))  # 会话标题，服务端归一空白后截断到 80 字
    # 最初进入画布的素材：会话的「源头」，切图不改它（RESTRICT：还有会话引用时不许删素材）
    original_asset_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("assets.id", ondelete="RESTRICT")
    )
    # 当前画布显示的素材：切图（switch_current）时更新
    current_asset_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("assets.id", ondelete="RESTRICT")
    )
    # 采用候选或切换图片墙时递增，用于判定旧选区已失效
    revision: Mapped[int] = mapped_column(default=1)
    # 画布文档（app/layers.py 的 LayerDocument 序列化）：整份 JSON 存一列，整体读写
    document: Mapped[dict] = mapped_column(JSONB, default=dict)
    # 最后更新时间：会话列表按它倒序排列（server_default 建行时给值，onupdate 每次更新刷新）
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, server_default=func.now(), onupdate=func.now()
    )


class SessionAsset(Base):
    """会话图片墙。未采用的候选一并留存，切换当前图不覆盖任何已有结果。

    复合主键 (session_id, asset_id) 天然去重——同一张图在同一会话只会出现一次。
    """

    __tablename__ = "session_assets"

    # 联合主键之一：所属会话，删会话级联删关联行
    session_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("edit_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    # 联合主键之二：墙上的素材
    asset_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True
    )
    # 同一事务内插入多行的时间戳相同，靠显式序号保证图片墙顺序稳定
    position: Mapped[int]
