# 图像模型适配层的抽象基座：定义所有 provider 必须遵守的协议、统一入参与错误类型。
# 调用方（services/generation.py）只依赖这里的 Protocol 与 GenerateRequest，不关心底下
# 接的是 mock 还是某个真实平台——因此新增平台无需改动调用方，只在此层加实现即可。
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Protocol

# 进度回调类型别名：入参为 (进度百分比, 阶段文案)、异步执行、无返回。
# 各 adapter 在生成过程中调用它上报进度，最终经 runs.report 落库并广播给 SSE 客户端。
ProgressCallback = Callable[[int, str], Awaitable[None]]


# 统一的领域异常：模型服务不可用或返回失败时抛出。
# 上层 generation.execute 捕获它落成 failed 终态，并把错误消息透传给前端。
class ProviderError(Exception):
    """模型服务不可用或返回失败。"""


# 一次生成请求的全部入参，由 generation.execute 组装后交给具体 adapter。
# @dataclass(frozen=True)：自动生成 __init__ 等样板方法；frozen 令实例不可变——
# 请求一旦构造就不应中途改写，也便于安全地在多个协程间共享传递。
@dataclass(frozen=True)
class GenerateRequest:
    prompt: str  # 正向提示词，描述想要的画面
    width: int  # 目标宽（像素），由输出比例换算而来
    height: int  # 目标高（像素）
    count: int = 1  # 需要生成的候选图张数
    negative_prompt: str | None = None  # 反向提示词，排除不想要的元素，可空
    seed: int | None = None  # 随机种子，固定后可复现同一构图，可空
    # 参考图以原始字节传入，由各 adapter 决定编码方式
    references: list[bytes] = field(default_factory=list)


# ImageProvider 是一个 Protocol（结构化类型/鸭子类型契约）：任何类只要具备 name 属性和
# 同签名的 generate 方法，就“算”一个合法 provider，无需显式继承本类。调用方按此协议编程，
# 与具体实现彻底解耦——这正是“新增平台不改调用方”能成立的根基。
class ImageProvider(Protocol):
    name: str  # provider 标识（如 mock/dashscope/openai），与配置项 image_provider 对应

    # 生成方法：所有 adapter 的统一入口，也是本 Protocol 唯一要求实现的行为。
    # 入参：request 生成请求；on_progress 可选进度回调（传入则在关键节点回报进度）。
    # 出参：count 张图片的原始字节列表。约定——任何失败都抛 ProviderError，不返回空列表。
    async def generate(
        self, request: GenerateRequest, on_progress: ProgressCallback | None = None
    ) -> list[bytes]:
        """返回 count 张图片的原始字节。失败时抛出 ProviderError。"""
        ...
