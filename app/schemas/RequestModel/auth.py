#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/23 10:52
# @Author     : fany
# @Project    : PyCharm
# @File       : auth.py
# @Description:
from pydantic import BaseModel, Field, field_validator
from typing import Annotated


class CallbackRequest(BaseModel):
    """回调地址生成请求模型"""

    merchant_id: Annotated[
        str,
        Field(
            description="商户ID",
            examples=["merchant001"]
        )
    ]

    @field_validator('merchant_id')
    def validate_merchant_id(cls, v):
        if not v or not v.strip():
            raise ValueError('商户ID不能为空')
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "merchant_id": "merchant001"
            }
        }
    }


class AutoLoginRequest(BaseModel):
    """自动登录请求模型"""

    merchant_id: Annotated[
        str,
        Field(
            description="商户ID，唯一标识",
            examples=["merchant001"]
        )
    ]

    app_key: Annotated[
        str,
        Field(
            description="比邻应用Key",
            examples=["your_app_key_here"]
        )
    ]

    app_secret: Annotated[
        str,
        Field(
            description="比邻应用密钥",
            examples=["your_app_secret_here"]
        )
    ]

    @field_validator('merchant_id', 'app_key', 'app_secret')
    def validate_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('字段不能为空')
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "merchant_id": "merchant001",
                "app_key": "your_app_key_here",
                "app_secret": "your_app_secret_here"
            }
        }
    }