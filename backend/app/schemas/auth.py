# 账号相关的 Pydantic 模型：登录/注册入参校验与用户出参
import uuid  # UserOut.id 的 UUID 类型

from pydantic import BaseModel, Field, field_validator  # 基类、字段约束、字段校验器


# 入参模型：注册与登录共用的凭据（用户名 + 密码），带长度约束
class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32)  # 用户名长度 3-32
    # 密码：仅校验长度 6-64，哈希在 security.py 完成，绝不存明文
    password: str = Field(min_length=6, max_length=64)

    # @field_validator("username")：对 username 字段做入参级自定义校验
    @field_validator("username")
    # @classmethod：校验器是类方法，cls 为模型类、value 为待校验值
    @classmethod
    def _normalize(cls, value: str) -> str:
        normalized = value.strip()  # 去除首尾空白，避免空格污染用户名
        # 去掉下划线后须全为字母或数字，即只允许字母、数字、下划线
        if not normalized.replace("_", "").isalnum():
            raise ValueError("用户名只能包含字母、数字和下划线")  # 触发 422 校验错误
        return normalized  # 返回规范化后的值，实际入库/比对用它


# 出参模型：对外只暴露 id 与用户名，绝不返回密码哈希
class UserOut(BaseModel):
    id: uuid.UUID  # 用户主键
    username: str  # 用户名

    # from_attributes=True：允许从 ORM 对象属性直接构造（旧称 orm_mode）
    model_config = {"from_attributes": True}
