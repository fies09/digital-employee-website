#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/22 16:56
# @Author     : fany
# @Project    : PyCharm
# @File       : settings.py
# @Description:
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from app.utils.common import generate_secret_key


# 获取项目根目录路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 加载.env文件
load_dotenv(BASE_DIR / ".env")

class Settings(BaseSettings):
    # 项目基本信息
    PROJECT_NAME: str = "数字员工系统"
    PROJECT_DESCRIPTION: str = "基于比邻平台的数字员工管理系统API"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # 调试模式
    DEBUG: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore',  # 添加这行来忽略额外的环境变量
    )

    # JWT配置
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", generate_secret_key())
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 2  # access token过期时间（小时）
    JWT_REFRESH_DAYS: int = 7  # refresh token过期时间（天）

    # 数据库配置
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str

    # 数据库连接池配置
    DB_POOL_SIZE: int = 10
    DB_POOL_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600  # 1小时
    DB_ECHO: bool = False

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    LOG_PATH: Path = BASE_DIR / "logs"

    OPENAI_API_KEY: str
    OPENAI_API_BASE: str
    MODEL_NAME: str
    EMBEDDINGS_MODEL_NAME: str

    NUM_THREADS: int  # 线程数

    # langchain根目录
    LANGCHAIN_ROOT_PATH: str = str(BASE_DIR / "app/langchain")

    # cpu个数
    CPU_NUM: int = os.cpu_count() - 1

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """异步数据库连接URL（如果需要）"""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS配置
    ALLOWED_ORIGINS: list = ["*"]  # 生产环境应该设置具体域名
    ALLOWED_METHODS: list = ["*"]
    ALLOWED_HEADERS: list = ["*"]

    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", generate_secret_key())

def initialize_settings() -> Settings:
    """初始化设置并创建必要的目录"""
    settings = Settings()

    # 创建日志目录
    settings.LOG_PATH.mkdir(parents=True, exist_ok=True)

    return settings

settings = initialize_settings()
