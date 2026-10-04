# 图片校验与元信息提取的统一入口。所有图片入口都应复用 probe，不要在各处重复校验。
import io
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

# 单文件字节上限 20MB：超限直接拒收，不进入解码。
MAX_FILE_BYTES = 20 * 1024 * 1024
# 像素总量上限 5000 万：防「解压炸弹」——文件很小但解码后撑爆内存。
MAX_PIXELS = 50_000_000
# 最短边下限 32 像素：过小的图基本没有编辑价值。
MIN_SIDE = 32

# 受支持格式 → MIME 类型。只认这三种，键名是 Pillow 解码得到的 format。
ALLOWED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
# 受支持格式 → 落地文件扩展名。
EXTENSIONS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


# 领域异常：图片校验未通过。由 probe 抛出，routers/assets.py 翻译成 422。
class ImageRejected(Exception):
    pass


# probe 的返回值：一张图经校验后的元信息，全部来自实际解码结果，可信。
@dataclass(frozen=True)
class ImageMeta:
    image_format: str
    content_type: str
    extension: str
    width: int
    height: int
    size_bytes: int
    has_alpha: bool


# 校验图片并提取元信息。入参：data 原始字节；出参：ImageMeta；任一项不合规抛 ImageRejected。
def probe(data: bytes) -> ImageMeta:
    """校验图片并提取元信息。格式以实际解码结果为准，不采信文件扩展名。"""
    # 空文件直接拒。
    if not data:
        raise ImageRejected("文件为空")
    # 字节数上限，与路由层的 413 判断重复一层，确保任何入口都被兜住。
    if len(data) > MAX_FILE_BYTES:
        raise ImageRejected(f"文件超过 {MAX_FILE_BYTES // 1024 // 1024} MB 上限")

    try:
        with Image.open(io.BytesIO(data)) as image:
            # format 由 Pillow 按实际字节内容识别，不看扩展名/Content-Type，防伪造后缀。
            image_format = image.format or ""
            width, height = image.size
            # 依据色彩模式或 info 判断是否含透明通道（抠图/PNG/WebP 结果关心这个）。
            has_alpha = image.mode in {"RGBA", "LA", "PA"} or "transparency" in image.info
            # 触发完整解码以暴露截断或损坏的数据
            # open() 只读文件头（惰性），load() 才真正解码全部像素；
            # 截断/损坏的文件正是在 load() 这一步才抛错，故必须显式调用。
            image.load()
    # 无法识别/解码出错/超大解压炸弹统一按「非法图片」处理；from exc 保留底层原因。
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ImageRejected("文件已损坏或不是受支持的图片") from exc

    # 以下三项都基于「解码后」的真实结果判断，而非任何客户端上报值。
    # 1) 格式白名单。
    if image_format not in ALLOWED_FORMATS:
        raise ImageRejected("仅支持 JPG、PNG 与 WebP")
    # 2) 最短边下限。
    if min(width, height) < MIN_SIDE:
        raise ImageRejected(f"图片过小，最短边需不小于 {MIN_SIDE} 像素")
    # 3) 像素总量上限。
    if width * height > MAX_PIXELS:
        raise ImageRejected("图片像素总量过大")

    # 全部通过，返回可信元信息；size_bytes 用原始字节长度。
    return ImageMeta(
        image_format=image_format,
        content_type=ALLOWED_FORMATS[image_format],
        extension=EXTENSIONS[image_format],
        width=width,
        height=height,
        size_bytes=len(data),
        has_alpha=has_alpha,
    )
