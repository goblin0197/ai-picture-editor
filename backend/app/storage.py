# 对象存储封装（S3/MinIO）。全项目只经本模块访问对象存储，不直接调 boto3。
import asyncio
from functools import lru_cache

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import get_settings


# 私有：构造并缓存 boto3 S3 客户端。
# lru_cache 让整个进程复用同一个 client：创建开销不小且线程安全，复用免去反复建连。
# 签名版本固定 s3v4（MinIO 与 AWS 均支持）。
@lru_cache
def _client():
    settings = get_settings()
    return boto3.client(
        "s3",
        # endpoint 指向自建 MinIO；它同时决定签名 URL 里的 host（见 signed_url）。
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


# 确保桶存在：不存在则创建，幂等可反复调用。
# main.py 的 lifespan 启动时会调它，健康检查也会调，故无需手工建桶。
def ensure_bucket() -> None:
    bucket = get_settings().s3_bucket
    try:
        # head_bucket 探测桶是否存在（存在则无异常）。
        _client().head_bucket(Bucket=bucket)
    # 不存在（或无权限探测）会抛 ClientError，据此创建。
    except ClientError:
        _client().create_bucket(Bucket=bucket)


# 上传对象。boto3 是同步库，用 to_thread 丢线程池，避免阻塞事件循环。
# 入参：key 对象键；data 字节；content_type MIME 类型。
async def put(key: str, data: bytes, content_type: str) -> None:
    await asyncio.to_thread(
        _client().put_object,
        Bucket=get_settings().s3_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )


# 下载对象为字节。同样用 to_thread 包住同步调用。入参：key；出参：对象字节。
async def get(key: str) -> bytes:
    response = await asyncio.to_thread(
        _client().get_object, Bucket=get_settings().s3_bucket, Key=key
    )
    return response["Body"].read()


# 删除对象。同步调用包进线程池。入参：key。
async def delete(key: str) -> None:
    await asyncio.to_thread(_client().delete_object, Bucket=get_settings().s3_bucket, Key=key)


# 为对象签发短时可访问 URL。入参：key；出参：带签名参数的完整链接。
def signed_url(key: str) -> str:
    """生成短时签名 URL。纯本地计算，不产生网络请求。"""
    settings = get_settings()
    # host 取自 S3_ENDPOINT，它决定链接能否被打开：签名把 host 也算进去
    # （X-Amz-SignedHeaders=host），事后手工改地址会导致签名不匹配，必须由后端重新签发。
    # 有效期由 s3_url_ttl 控制。
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": key},
        ExpiresIn=settings.s3_url_ttl,
    )
