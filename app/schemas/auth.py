#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/21 14:52
# @Author     : fany
# @Project    : PyCharm
# @File       : auth.py
# @Description:
from pydantic import BaseModel, validator
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int = 3600 * 24  # 24小时

class AutoRegisterRequest(BaseModel):
    """自动注册请求"""
    app_key: str
    app_secret: str
    callback_address: str

    @validator('app_key')
    def validate_app_key(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('应用key不能为空')
        return v.strip()

    @validator('app_secret')
    def validate_app_secret(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('应用密钥不能为空')
        return v.strip()

    @validator('callback_address')
    def validate_callback_address(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('回调地址不能为空')
        # 简单的URL格式验证
        if not v.startswith(('http://', 'https://')):
            raise ValueError('回调地址格式不正确')
        return v.strip()

class MerchantInfo(BaseModel):
    """商户信息响应"""
    id: int
    merchant_id: str
    app_key: str
    callback_address: str
    user_source: str
    is_active: bool
    is_registered: bool  # 是否已完成注册

    class Config:
        from_attributes = True
