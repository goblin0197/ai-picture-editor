# 素材表 ORM 模型：记录每张图片的存储位置与元数据（尺寸、格式等）
import enum  # 用于定义素材类别与来源两个字符串枚举
import uuid  # 外键 user_id 的 UUID 类型

from sqlalchemy import ForeignKey, String  # 外键约束与 VARCHAR 列类型
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # PG 原生 UUID 列类型
from sqlalchemy.orm import Mapped, mapped_column  # 映射类型注解与列构造器

from app.models.base import UUIDBase, enum_column  # 基类与枚举列工厂


# 素材类别枚举：一张图在流水线中的角色（原图/生成图/主体/背景/蒙版等）
class AssetKind(enum.StrEnum):
    ORIGINAL = "original"  # 用户上传的原始图
    GENERATED = "generated"  # 文生图产出的候选图
    SUBJECT = "subject"  # 抠出的主体（前景）
    BACKGROUND = "background"  # 背景图
    MASK = "mask"  # 蒙版（用于局部修改）
    MARKETING = "marketing"  # 营销/成品图
    EXPORT = "export"  # 导出成品


# 素材来源枚举：这张图是怎么进入系统的
class AssetSource(enum.StrEnum):
    UPLOAD = "upload"  # 用户上传
    GENERATE = "generate"  # 模型生成
    TOOL = "tool"  # 工具处理产出（如抠图/换背景）


# 素材记录，对应数据库表 assets，继承 UUIDBase 得到 id 与 created_at
class Asset(UUIDBase):
    __tablename__ = "assets"  # 表名 assets

    # 归属用户外键：ondelete=CASCADE 使删用户时其素材一并删除；建索引便于按用户查询
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # 素材类别：以 VARCHAR 存枚举 value（见 enum_column）
    kind: Mapped[AssetKind] = mapped_column(enum_column(AssetKind))
    # 素材来源：同样以 VARCHAR 存枚举 value
    source: Mapped[AssetSource] = mapped_column(enum_column(AssetSource))
    # 对象存储中的 key：唯一（unique），格式形如 users/<user_id>/...
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    image_format: Mapped[str] = mapped_column(String(8))  # 实际解码格式，如 png/jpeg
    width: Mapped[int]  # 图片宽（像素），无 mapped_column 时按类型推断为普通列
    height: Mapped[int]  # 图片高（像素）
    size_bytes: Mapped[int]  # 文件字节数
    has_alpha: Mapped[bool]  # 是否含透明通道（抠图结果通常为 True）
