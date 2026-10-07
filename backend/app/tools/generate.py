# 文生图工具的注册规格：把既有的 generation.execute 包装成统一 ToolSpec。
from app.schemas.run import GenerateIn
from app.services import generation
from app.tools.base import ToolSpec

GENERATE_IMAGE = ToolSpec(
    name="generate_image",
    label="生成图片",
    # description 直接影响规划模型何时选它：强调「从零生成」，与后续的编辑类工具划清边界
    description=(
        "根据文字描述从零生成图片候选。没有可编辑的图片，"
        "或用户明确要求换一张全新画面时使用；修改现有图片不要用它。"
    ),
    params=GenerateIn,  # 复用 /api/generations 的同一套参数校验
    handler=generation.execute,
    # 参考图 id 与种子由服务端从上下文/参数补齐，不给模型自由发挥的空间
    agent_hidden=("seed", "reference_asset_ids"),
)
