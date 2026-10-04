# mock 图像提供方：本项目的默认 provider（IMAGE_PROVIDER=mock）。
# 完全在本地用 Pillow 画占位图，不联网、不消耗任何真实额度，开发与测试全程跑在它上面。
# 关键设计：构图完全由“提示词哈希”决定，所以同一提示词每次得到相同结果——
# 既方便测试断言（可预期尺寸/张数），也让示例图稳定可复现。
import asyncio  # 用 sleep 模拟每张图的生成耗时，让进度回调看起来像真在跑
import colorsys  # 用 HLS→RGB 把哈希算出的色相转成配色
import hashlib  # 对提示词取 sha256，作为决定构图的随机种子
import io  # 把 Pillow 图像编码进内存缓冲，取字节而不落盘

from PIL import Image, ImageDraw

from app.providers.base import GenerateRequest, ImageProvider, ProgressCallback

# 每张图之间的模拟延时（秒）：制造分步进度的观感，也给 SSE 一点时间推送中间帧。
_STEP_DELAY = 0.4


# 遵守 ImageProvider 协议的占位图实现（这里显式继承只为表达意图，Protocol 本不强制）。
class MockImageProvider(ImageProvider):
    """本地占位图实现，不产生真实调用费用。构图由提示词哈希决定，同一提示词结果稳定。"""

    name = "mock"  # provider 标识，与配置值 IMAGE_PROVIDER=mock 对应

    # 生成入口：按 count 逐张“画”图并上报进度，返回每张的 PNG 字节。
    # 入参：request 生成请求；on_progress 可选进度回调。出参：图片字节列表。
    async def generate(
        self, request: GenerateRequest, on_progress: ProgressCallback | None = None
    ) -> list[bytes]:
        images: list[bytes] = []
        # 用提示词哈希的前 8 位十六进制作种子：同一提示词恒得同一 seed，构图因此稳定复现。
        seed = int(hashlib.sha256(request.prompt.encode()).hexdigest()[:8], 16)

        for index in range(request.count):
            await asyncio.sleep(_STEP_DELAY)  # 模拟耗时，让进度分步推进而非瞬间完成
            if on_progress:
                # 按已完成张数折算百分比并回报，前端进度条据此推进。
                progress = int((index + 1) / request.count * 100)
                await on_progress(progress, f"生成第 {index + 1} / {request.count} 张")
            # 每张用 seed + 偏移派生不同构图；乘 977（质数）让相邻张差异明显、又保持确定性。
            images.append(self._render(request, seed + index * 977, index))

        return images

    # 私有：把一个种子渲染成一张 PNG 占位图。全程纯计算、无随机源，故结果由 seed 唯一决定。
    # 入参：request 提供画布尺寸与提示词；seed 决定配色；index 影响圆的大小并标注序号。
    def _render(self, request: GenerateRequest, seed: int, index: int) -> bytes:
        hue = (seed % 360) / 360  # 种子取模 360 得色相角，再归一化到 0-1 供 colorsys 使用
        # 背景色：由色相生成的一种低明度、低饱和的沉稳底色。
        base = tuple(int(c * 255) for c in colorsys.hls_to_rgb(hue, 0.82, 0.38))
        # 前景强调色：色相旋转 180 度（+0.5）取对比色，用于画中心圆。
        accent = tuple(int(c * 255) for c in colorsys.hls_to_rgb((hue + 0.5) % 1, 0.45, 0.5))

        image = Image.new("RGB", (request.width, request.height), base)  # 按目标尺寸建底图
        draw = ImageDraw.Draw(image)  # 拿到绘图句柄，用于画圆和写字

        short = min(request.width, request.height)  # 取短边作基准，保证圆在任意比例下都不出界
        cx, cy = request.width // 2, request.height // 2  # 画布中心坐标
        radius = short // 3 + (index % 3) * short // 24  # 半径随序号轻微变化，多张之间有区分
        # 以中心为基准画实心圆（左上、右下两点确定外接矩形）。
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=accent)
        # 左上角写上截断后的提示词与序号，便于肉眼区分是哪条提示词的第几张。
        draw.text((16, 16), f"{request.prompt[:40]}\n#{index + 1}", fill=(255, 255, 255))

        buffer = io.BytesIO()  # 内存缓冲，避免写临时文件
        image.save(buffer, format="PNG")  # 编码为 PNG 写入缓冲
        return buffer.getvalue()  # 取出字节返回，与其他 provider 的返回形态一致
