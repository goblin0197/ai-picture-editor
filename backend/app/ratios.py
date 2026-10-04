# 输出比例的枚举及其对应像素尺寸，全项目统一以此为准，避免各处硬编码尺寸。
import enum


class Ratio(enum.StrEnum):
    """支持的画面比例。继承 StrEnum，成员本身即字符串（值就是 "1:1" 等），

    可直接参与 JSON 序列化、与前端传来的字符串比较，无需再取 .value。
    """

    SQUARE = "1:1"  # 方形
    PORTRAIT_4_5 = "4:5"  # 竖版 4:5
    PORTRAIT_3_4 = "3:4"  # 竖版 3:4
    VERTICAL_9_16 = "9:16"  # 竖版 9:16（如手机全屏）
    LANDSCAPE_16_9 = "16:9"  # 横版 16:9


# 与交付尺寸对齐，避免生成后再次重采样
# 每个比例映射到 (宽, 高) 像素；短边统一取 1080，保证清晰度一致。
SIZES: dict[Ratio, tuple[int, int]] = {
    Ratio.SQUARE: (1080, 1080),
    Ratio.PORTRAIT_4_5: (1080, 1350),
    Ratio.PORTRAIT_3_4: (1080, 1440),
    Ratio.VERTICAL_9_16: (1080, 1920),
    Ratio.LANDSCAPE_16_9: (1920, 1080),
}

# 默认对外交付的比例子集（并非全部比例都默认导出），生成/导出时按此清单产图。
DELIVERY_RATIOS = (Ratio.SQUARE, Ratio.PORTRAIT_4_5, Ratio.VERTICAL_9_16)


def size_of(ratio: Ratio) -> tuple[int, int]:
    """按比例枚举取出对应的 (宽, 高) 像素尺寸。"""
    return SIZES[ratio]
