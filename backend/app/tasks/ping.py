# 最小 ARQ 任务：不做任何业务，仅用来验证“投递端 → Redis 队列 → worker 消费”链路是否通。
# 同样需登记进 TASKS 才会被 worker 加载；签名遵循 ARQ 约定，首参为 worker 上下文 ctx。
async def ping(ctx: dict) -> str:
    """用于验证 API 到 worker 的投递链路是否连通。"""
    return "pong"  # 能拿到这个返回值，说明整条投递-消费链路已打通
