# 文生图相关的 Pydantic 模型：生成入参 GenerateIn 与任务出参 RunOut
import uuid  # 参考图 ID 与任务 ID 的 UUID 类型
from typing import Annotated  # 给字段附加 Field 约束的类型注解写法

from pydantic import BaseModel, Field, field_validator  # 基类、字段约束、字段校验器

from app.models.tool_run import RunStatus, ToolRun  # 任务状态枚举与任务 ORM 模型
from app.ratios import Ratio  # 输出比例枚举（尺寸见 ratios.py）
from app.schemas.asset import AssetOut  # 候选图出参模型

MAX_PROMPT = 1500  # 提示词/负向提示词的最大长度
MAX_REFERENCES = 3  # 单次请求最多允许的参考图数量


# 文生图入参模型：一次生成请求的全部参数与校验
class GenerateIn(BaseModel):
    # 提示词：必填，长度 1-MAX_PROMPT；下方校验器还会去空白并禁止纯空白
    prompt: Annotated[str, Field(min_length=1, max_length=MAX_PROMPT)]
    ratio: Ratio = Ratio.SQUARE  # 输出比例，默认正方形（见 ratios.py）
    count: Annotated[int, Field(ge=1, le=6)] = 4  # 候选图数量 1-6，默认 4
    # 负向提示词：可选，最长 MAX_PROMPT；空串会被校验器归一为 None
    negative_prompt: Annotated[str | None, Field(max_length=MAX_PROMPT)] = None
    # 随机种子：可选，范围为 32 位有符号整数上限，用于复现同一结果
    seed: Annotated[int | None, Field(ge=0, le=2147483647)] = None
    # 参考图素材 ID 列表：可选，最多 MAX_REFERENCES 张
    reference_asset_ids: Annotated[list[uuid.UUID], Field(max_length=MAX_REFERENCES)] = []

    # @field_validator("prompt")：校验 prompt 字段
    @field_validator("prompt")
    # @classmethod：校验器为类方法
    @classmethod
    def _require_prompt(cls, value: str) -> str:
        value = value.strip()  # 去首尾空白
        if not value:  # 去空白后为空则拒绝
            raise ValueError("提示词不能为空")
        return value

    # @field_validator("negative_prompt")：校验/归一 negative_prompt 字段
    @field_validator("negative_prompt")
    # @classmethod：校验器为类方法
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        # 有值则去空白，空串归一为 None；本就是 None 直接返回 None
        return value.strip() or None if value else None


# 任务出参模型：把 ToolRun 状态与候选图一起返回给前端轮询/展示
class RunOut(BaseModel):
    id: uuid.UUID  # 任务主键（同时是队列 job id）
    tool: str  # 工具名
    status: RunStatus  # 当前状态（queued/running 等）
    progress: int  # 进度 0-100
    stage: str  # 当前阶段文案
    error: str | None  # 失败原因，成功/进行中为 None
    prompt: str | None = None  # 发起任务时的提示词（编辑会话用它回显素材名，可能为 None）
    candidates: list[AssetOut] = []  # 候选图列表，默认空

    # @classmethod：工厂方法，从 ToolRun 与候选图列表构造出参
    @classmethod
    def of(cls, run: ToolRun, candidates: list[AssetOut] | None = None) -> "RunOut":
        return cls(
            id=run.id,
            tool=run.tool,
            status=run.status,
            progress=run.progress,
            stage=run.stage,
            error=run.error,
            # params 是 JSONB：提示词存在发起时的入参里，这里回填给前端展示
            prompt=run.params.get("prompt"),
            candidates=candidates or [],  # 未传候选图时用空列表兜底
        )
