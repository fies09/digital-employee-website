#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/21 14:48
# @Author     : fany
# @Project    : PyCharm
# @File       : auth.py - Response Models
# @Description: 响应模型定义
from typing import Optional, List, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field

# 泛型类型变量
T = TypeVar('T')

class UnregisteredResponse(BaseModel):
    """未注册状态响应模型"""
    merchant_id: str = Field(..., description="商户ID")
    is_registered: bool = Field(False, description="是否已注册")
    status: str = Field("unregistered", description="状态")
    cache_id: str = Field(..., description="缓存ID")
    register_url: str = Field(..., description="注册地址")
    expires_at: str = Field(..., description="缓存过期时间")
    attempt_count: int = Field(1, description="尝试次数")
    message: str = Field(..., description="提示信息")

    class Config:
        schema_extra = {
            "example": {
                "merchant_id": "MERCHANT_001",
                "is_registered": False,
                "status": "unregistered",
                "cache_id": "cache_67890",
                "register_url": "/api/v1/auth/auto-login",
                "expires_at": "2025-05-26T11:30:00Z",
                "attempt_count": 1,
                "message": "请提供client_id和client_secret进行自动注册"
            }
        }

class BilinCredentialsResponse(BaseModel):
    """比邻平台凭证验证响应模型"""
    code: int = Field(..., description="比邻平台响应码")
    message: str = Field(..., description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="比邻平台返回的数据")
    extra: Optional[Any] = Field(None, description="额外信息")
    path: Optional[str] = Field(None, description="请求路径")
    timestamp: Optional[int] = Field(None, description="时间戳")

    class Config:
        schema_extra = {
            "example": {
                "code": 0,
                "data": {
                    "expired": "2021-06-17 17:55:10",
                    "expiredTime": 1623923710000,
                    "value": "b56ffe33-faf9-4e2e-8f3f-851c43a79f0d"
                },
                "extra": None,
                "message": "success",
                "path": "",
                "timestamp": 1623837310728
            }
        }


class RefreshTokenResponse(BaseModel):
    """刷新令牌响应模型"""
    access_token: str = Field(..., description="新的访问令牌")
    token_type: str = Field("Bearer", description="令牌类型")
    expires_in: int = Field(..., description="令牌过期时间（秒）")

    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "token_type": "Bearer",
                "expires_in": 7200
            }
        }

class CacheStatistics(BaseModel):
    """缓存统计信息模型"""
    total_unregistered: int = Field(..., description="未注册商户总数")
    total_registered: int = Field(0, description="已注册商户总数")
    cache_keys: List[Dict[str, Any]] = Field([], description="缓存键列表")
    summary_by_attempts: Dict[str, int] = Field({}, description="按尝试次数统计")
    summary_by_status: Dict[str, int] = Field({}, description="按状态统计")

    class Config:
        schema_extra = {
            "example": {
                "total_unregistered": 5,
                "total_registered": 10,
                "cache_keys": [
                    {
                        "merchant_id": "MERCHANT_001",
                        "cache_id": "cache_12345",
                        "attempt_count": 2,
                        "created_at": "2025-05-26T10:30:00Z",
                        "status": "unregistered"
                    }
                ],
                "summary_by_attempts": {
                    "1": 3,
                    "2": 1,
                    "3": 1
                },
                "summary_by_status": {
                    "unregistered": 5,
                    "registered": 10
                }
            }
        }

class RedisConfig(BaseModel):
    """Redis配置模型"""
    host: str = Field("localhost", description="Redis主机")
    port: int = Field(6379, description="Redis端口")
    db: int = Field(0, description="Redis数据库编号")
    password: Optional[str] = Field(None, description="Redis密码")
    decode_responses: bool = Field(True, description="是否解码响应")
    socket_connect_timeout: int = Field(5, description="连接超时时间")
    socket_timeout: int = Field(5, description="Socket超时时间")

    class Config:
        schema_extra = {
            "example": {
                "host": "localhost",
                "port": 6379,
                "db": 0,
                "password": None,
                "decode_responses": True,
                "socket_connect_timeout": 5,
                "socket_timeout": 5
            }
        }

class BaseResponse(BaseModel, Generic[T]):
    """通用响应模型基类"""
    code: int = Field(description="状态码")
    message: str = Field(description="响应消息")
    success: bool = Field(description="是否成功")
    data: Optional[T] = Field(default=None, description="响应数据")
    timestamp: str = Field(description="时间戳")
    request_id: Optional[str] = Field(default=None, description="请求ID")

    model_config = {
        "json_schema_extra": {
            "example": {
                "code": 200,
                "message": "操作成功",
                "success": True,
                "data": None,
                "timestamp": "2025-05-27T10:30:00",
                "request_id": "req_1234567890"
            }
        }
    }


# ============ 修复3: 认证相关响应模型 ============
class MerchantInfo(BaseModel):
    """商户信息模型"""
    merchant_id: str = Field(description="商户ID")
    client_id: str = Field(description="客户端ID")
    app_key: str = Field(description="应用密钥")
    callback_address: str = Field(description="回调地址")
    is_active: bool = Field(description="是否激活")


class AuthInfo(BaseModel):
    """认证信息模型"""
    access_token: str = Field(description="访问令牌")
    refresh_token: str = Field(description="刷新令牌")
    token_type: str = Field(description="令牌类型")
    expires_in: int = Field(description="过期时间(秒)")
    refresh_expires_in: int = Field(description="刷新令牌过期时间(秒)")


class LoginResponse(BaseModel):
    """登录响应数据模型"""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    merchant_id: str
    user_source: str
    callback_url: str
    is_registered: bool
    status: str
    merchant_info: dict  # 新增
    auth_info: dict  # 新增
    bilin_response: Optional[dict]  # 新增
    integration_status: str  # 新增

    model_config = {
        "json_schema_extra": {
            "example": {
                "merchant_info": {
                    "merchant_id": "merchant_001",
                    "client_id": "bilin_client_123",
                    "app_key": "generated_unique_key",
                    "callback_address": "https://yourserver.com/api/v1/auth/callback/merchant_001_randomstring",
                    "is_active": True
                },
                "auth_info": {
                    "access_token": "jwt_token...",
                    "refresh_token": "jwt_refresh_token...",
                    "token_type": "Bearer",
                    "expires_in": 7200,
                    "refresh_expires_in": 604800
                },
                "bilin_response": {"code": 0, "message": "success"},
                "integration_status": "success"
            }
        }
    }


# ============ 修复4: 错误响应模型 ============
class ErrorDetail(BaseModel):
    """错误详情模型"""
    error_code: Optional[str] = Field(default=None, description="错误码")
    error_message: str = Field(description="错误消息")
    field: Optional[str] = Field(default=None, description="错误字段")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    code: int = Field(description="HTTP状态码")
    message: str = Field(description="错误消息")
    success: bool = Field(default=False, description="是否成功")
    data: Optional[Dict[str, Any]] = Field(default=None, description="错误详情")
    timestamp: str = Field(description="时间戳")
    request_id: Optional[str] = Field(default=None, description="请求ID")

    model_config = {
        "json_schema_extra": {
            "example": {
                "code": 400,
                "message": "请求参数错误",
                "success": False,
                "data": None,
                "timestamp": "2025-05-27T10:30:00",
                "request_id": "req_1234567890"
            }
        }
    }
