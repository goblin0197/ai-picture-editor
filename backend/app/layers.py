"""画布文档结构。工具只修改此文档，像素合成由渲染环节按文档执行。

这是「文档驱动」设计的核心：编辑器的每一步操作（抠图、换背景、加文字…）
都不直接碰像素，而是增删改这份 JSON 文档；真正的合成留到渲染/导出环节按文档执行。
文档以 JSONB 存在 EditSession.document 里，Pydantic 模型负责校验其结构。
"""

import enum  # 图层类别等枚举
import uuid  # 图层引用的素材 ID 类型

from pydantic import BaseModel, Field  # 文档模型基类与默认值工厂

from app.models import Asset  # 仅用于 document_of 的类型标注

# 底图图层的固定 id：拆层（抠主体/换背景）后底图会被主体层与背景层取代
BASE_LAYER_ID = "base"


class LayerKind(enum.StrEnum):
    """图层类别。继承 StrEnum 后可直接与 JSON 里的字符串比较、参与序列化。"""

    IMAGE = "image"  # 位图图层（引用一张素材）
    TEXT = "text"  # 文字图层（后续步骤实现）
    SHAPE = "shape"  # 形状图层（后续步骤实现）


class Transform(BaseModel):
    """相对画布左上角的位置与形变，缩放为倍率而非像素。

    用倍率的好处：画布尺寸变化（如多尺寸导出）时按比例换算即可，不用重算像素。
    """

    x: float = 0  # 左上角横坐标（画布坐标系，单位像素）
    y: float = 0  # 左上角纵坐标
    scale_x: float = 1  # 横向缩放倍率，1 为原始大小
    scale_y: float = 1  # 纵向缩放倍率
    rotation: float = 0  # 旋转角度（度）


class Layer(BaseModel):
    """单个图层：一份描述 + 一个形变，不含像素数据。

    asset_id 指向素材表（image 类图层必有）；width/height 是图层的固有尺寸
    （位图即其像素尺寸），实际显示大小 = 固有尺寸 × transform.scale。
    """

    id: str  # 图层 id（文档内唯一，底图固定为 BASE_LAYER_ID）
    kind: LayerKind  # 图层类别
    name: str  # 展示名（图层面板里可见，如「底图」「主体」）
    width: int  # 固有宽度（像素）
    height: int  # 固有高度（像素）
    asset_id: uuid.UUID | None = None  # 引用的素材；仅 image 图层有值
    transform: Transform = Field(default_factory=Transform)  # 位置与形变，默认原点原尺寸
    opacity: float = 1  # 不透明度 0~1
    visible: bool = True  # 是否可见（隐藏的图层不渲染）
    locked: bool = False  # 是否锁定（锁定后不可拖动/改形变，底图默认锁定）


class LayerDocument(BaseModel):
    """一份完整画布文档：画布尺寸 + 图层列表（列表顺序即图层叠放次序）。"""

    width: int  # 画布宽度（像素），取自底图素材的尺寸
    height: int  # 画布高度
    layers: list[Layer] = Field(default_factory=list)  # 图层从下到上排列


def document_of(asset: Asset) -> LayerDocument:
    """以整张图片作为底图建立文档。底图锁定，拆层后才会被主体与背景层取代。"""
    return LayerDocument(
        # 画布尺寸直接取素材尺寸——新会话的画布就是这张图本身
        width=asset.width,
        height=asset.height,
        layers=[
            Layer(
                id=BASE_LAYER_ID,  # 固定 id，便于前端识别底图
                kind=LayerKind.IMAGE,
                name="底图",
                width=asset.width,  # 底图铺满画布
                height=asset.height,
                asset_id=asset.id,  # 指向这张素材，渲染时经签名 URL 取图
                locked=True,  # 底图不可拖动，避免误操作
            )
        ],
    )
