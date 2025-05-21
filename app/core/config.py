#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/21 14:49
# @Author     : fany
# @Project    : PyCharm
# @File       : config.py
# @Description:
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "商户认证系统"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # 数据库配置
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@db:5432/merchant_auth"

    # Redis配置
    REDIS_URL: str = "redis://redis:6379/0"

    # JWT配置
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # 比邻系统配置
    BILIN_BASE_URL: str = "https://api.bilin.com"

    class Config:
        env_file = ".env"


settings = Settings()