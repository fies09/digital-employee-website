#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/21 14:52
# @Author     : fany
# @Project    : PyCharm
# @File       : auth.py
# @Description:
from pydantic import BaseModel, Field


class LoginResponse(BaseModel):
    """登录响应模型"""

    access_token: str = Field(description="访问令牌")
    refresh_token: str = Field(description="刷新令牌")
    token_type: str = Field(default="Bearer", description="令牌类型")
    expires_in: int = Field(description="令牌过期时间（秒）")
    merchant_id: str = Field(description="商户ID")
    user_source: str = Field(description="用户来源，U01=比邻用户，U02=网页端注册")
    callback_url: str = Field(description="回调地址")
    is_new_user: bool = Field(description="是否为新注册用户")

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "token_type": "Bearer",
                "expires_in": 7200,
                "merchant_id": "merchant001",
                "user_source": "U01",
                "callback_url": "https://api.example.com/api/auth/callback/merchant001",
                "is_new_user": False
            }
        }
    }


class CallbackResponse(BaseModel):
    """回调地址响应模型"""

    callback_url: str = Field(description="生成的回调地址")
    merchant_id: str = Field(description="商户ID")
    message: str = Field(description="响应消息")

    model_config = {
        "json_schema_extra": {
            "example": {
                "callback_url": "https://api.example.com/api/auth/callback/merchant001",
                "merchant_id": "merchant001",
                "message": "商户 merchant001 的回调地址已生成"
            }
        }
    }