from datetime import datetime

from pydantic import BaseModel, Field, field_validator, validator
from typing import TypeVar, Optional, Dict, Any
import re

# 泛型类型变量
T = TypeVar('T')

class ClientCredentialsRequest(BaseModel):
    """客户端凭证验证请求模型"""
    client_id: str = Field(..., min_length=1, max_length=100, description="比邻平台客户端ID")
    client_secret: str = Field(..., min_length=1, max_length=200, description="比邻平台客户端密钥")
    merchant_id: str = Field(..., min_length=1, max_length=50, description="商户唯一标识")

    @field_validator('client_id', mode='before')
    @classmethod
    def validate_client_id(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError('client_id不能为空')
        return v

    @field_validator('client_secret', mode='before')
    @classmethod
    def validate_client_secret(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError('client_secret不能为空')
        return v

    @field_validator('merchant_id', mode='before')
    @classmethod
    def validate_merchant_id(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError('merchant_id不能为空')
            # 商户ID格式验证：只允许字母、数字、下划线和短横线
            if not re.match(r'^[a-zA-Z0-9_-]+$', v):
                raise ValueError('merchant_id格式不正确，只允许字母、数字、下划线和短横线')
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "client_id": "your_client_id",
                "client_secret": "your_client_secret",
                "merchant_id": "merchant_001"
            }
        }
    }

class AutoLoginRequest(BaseModel):
    """原始自动登录请求模型"""
    merchant_id: str = Field(..., min_length=1, max_length=50, description="商户ID")

    class Config:
        schema_extra = {
            "example": {
                "merchant_id": "MERCHANT_001"
            }
        }


class EnhancedAutoLoginRequest(BaseModel):
    """增强版自动登录请求模型，支持可选凭证信息"""
    merchant_id: str = Field(..., min_length=1, max_length=50, description="商户ID")
    client_id: Optional[str] = Field(None, min_length=1, max_length=100,
                                     description="比邻平台客户端ID（可选，用于自动注册）")
    client_secret: Optional[str] = Field(None, min_length=1, max_length=200,
                                         description="比邻平台客户端密钥（可选，用于自动注册）")

    @validator('client_id', pre=True)
    def validate_client_id(cls, v):
        if v is not None and isinstance(v, str):
            v = v.strip()
            if not v:
                return None
        return v

    @validator('client_secret', pre=True)
    def validate_client_secret(cls, v):
        if v is not None and isinstance(v, str):
            v = v.strip()
            if not v:
                return None
        return v

    @validator('client_secret')
    def validate_credentials_pair(cls, v, values):
        """验证凭证信息必须成对提供"""
        client_id = values.get('client_id')

        # 如果提供了其中一个，必须同时提供另一个
        if (client_id is not None and v is None) or (client_id is None and v is not None):
            raise ValueError('client_id和client_secret必须同时提供或同时为空')

        return v

    class Config:
        schema_extra = {
            "example": {
                "merchant_id": "MERCHANT_001",
                "client_id": "your_client_id",
                "client_secret": "your_client_secret"
            }
        }


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求模型"""
    refresh_token: str = Field(..., min_length=1, description="刷新令牌")

    @validator('refresh_token', pre=True)
    def validate_refresh_token(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError('refresh_token不能为空')
        return v

    class Config:
        schema_extra = {
            "example": {
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
            }
        }


class MerchantStatusRequest(BaseModel):
    """商户状态查询请求模型"""
    merchant_id: str = Field(..., min_length=1, max_length=50, description="商户ID")
    include_cache: Optional[bool] = Field(False, description="是否包含缓存信息")

    class Config:
        schema_extra = {
            "example": {
                "merchant_id": "MERCHANT_001",
                "include_cache": True
            }
        }

class CallbackData:
    """回调数据模型"""
    def __init__(self, callback_id: str, data: Dict[str, Any]):
        self.callback_id = callback_id
        self.data = data
        self.timestamp = datetime.now()
        self.type = data.get('type', 'unknown')
