#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/22 16:56
# @Author     : fany
# @Project    : PyCharm
# @File       : settings.py
# @Description: 应用配置设置

import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from app.utils.common import generate_secret_key

# 获取项目根目录路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 加载.env文件
load_dotenv(BASE_DIR / ".env")


class Settings(BaseSettings):
    """应用配置类"""

    # ========== 项目基本信息 ==========
    PROJECT_NAME: str = "数字员工系统"
    PROJECT_DESCRIPTION: str = "基于比邻平台的数字员工管理系统API"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # ========== 环境配置 ==========
    ENVIRONMENT: str = Field(default="development", description="运行环境")
    DEBUG: bool = Field(default=True, description="调试模式")

    @validator('DEBUG', pre=True)
    def parse_debug(cls, v):
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return bool(v)

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.ENVIRONMENT.lower() == "development"

    # ========== 服务器配置 ==========
    HOST: str = Field(default="0.0.0.0", description="绑定地址")
    PORT: int = Field(default=8000, description="端口号")
    WORKERS: int = Field(default=1, description="工作进程数")

    @validator('WORKERS', pre=True)
    def validate_workers(cls, v, values):
        if values.get('DEBUG', True):
            return 1  # 开发模式使用单进程
        return max(1, min(int(v) if v else 4, os.cpu_count() or 4))

    # ========== 安全配置 ==========
    SECRET_KEY: str = Field(default_factory=generate_secret_key, description="应用密钥")
    JWT_SECRET_KEY: str = Field(default_factory=generate_secret_key, description="JWT密钥")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT算法")
    JWT_EXPIRE_HOURS: int = Field(default=2, description="访问令牌过期时间（小时）")
    JWT_REFRESH_DAYS: int = Field(default=7, description="刷新令牌过期时间（天）")

    # ========== CORS配置 ==========
    ALLOWED_ORIGINS: List[str] = Field(default=["*"], description="允许的源")
    ALLOWED_METHODS: List[str] = Field(default=["*"], description="允许的方法")
    ALLOWED_HEADERS: List[str] = Field(default=["*"], description="允许的头部")

    @validator('ALLOWED_ORIGINS', pre=True)
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            # 开发环境默认允许所有源
            if v == "*":
                return ["*"]
            return [origin.strip() for origin in v.split(',')]
        return v if v else ["*"]

    # ========== 数据库配置 ==========
    POSTGRES_USER: str = Field(..., description="数据库用户名")
    POSTGRES_PASSWORD: str = Field(..., description="数据库密码")
    POSTGRES_HOST: str = Field(default="localhost", description="数据库主机")
    POSTGRES_PORT: int = Field(default=5432, description="数据库端口")
    POSTGRES_DB: str = Field(..., description="数据库名称")

    # 数据库连接池配置
    DB_POOL_SIZE: int = Field(default=10, description="连接池大小")
    DB_POOL_OVERFLOW: int = Field(default=20, description="连接池溢出大小")
    DB_POOL_TIMEOUT: int = Field(default=30, description="连接池超时时间")
    DB_POOL_RECYCLE: int = Field(default=3600, description="连接回收时间")
    DB_ECHO: bool = Field(default=False, description="是否打印SQL")

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """同步数据库连接URL"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """异步数据库连接URL"""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # ========== Redis配置 ==========
    REDIS_HOST: str = Field(default="localhost", description="Redis主机")
    REDIS_PORT: int = Field(default=6379, description="Redis端口")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis密码")
    REDIS_DB: int = Field(default=0, description="Redis数据库")
    REDIS_MAX_CONNECTIONS: int = Field(default=10, description="Redis最大连接数")
    REDIS_TIMEOUT: int = Field(default=5, description="Redis连接超时时间")

    @property
    def REDIS_URL(self) -> str:
        """Redis连接URL"""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ========== 缓存配置 ==========
    CACHE_PREFIX: str = Field(default="auto_login", description="缓存前缀")
    CACHE_EXPIRE_TIME: int = Field(default=3600, description="缓存过期时间（秒）")
    MAX_LOGIN_ATTEMPTS: int = Field(default=5, description="最大登录尝试次数")

    # ========== 比邻平台配置 ==========
    BILIN_API_BASE: Optional[str] = Field(default=None, description="比邻平台API基础URL")
    CALLBACK_URL_PREFIX: str = Field(default="https://api.example.com/callback", description="回调地址前缀")

    @property
    def BILIN_LOGIN_ENDPOINT(self) -> Optional[str]:
        """比邻平台登录端点"""
        if self.BILIN_API_BASE:
            return f"{self.BILIN_API_BASE}/thirdparty/user/login/client"
        return None

    # ========== 日志配置 ==========
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    LOG_FORMAT: str = Field(
        default="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        description="日志格式"
    )
    LOG_PATH: Path = Field(default=BASE_DIR / "logs", description="日志路径")
    LOG_ROTATION: str = Field(default="1 day", description="日志轮转")
    LOG_RETENTION: str = Field(default="30 days", description="日志保留时间")

    # ========== AI配置 ==========
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API密钥")
    OPENAI_API_BASE: str = Field(default="https://api.openai.com/v1", description="OpenAI API基础URL")
    MODEL_NAME: str = Field(default="gpt-3.5-turbo", description="模型名称")
    EMBEDDINGS_MODEL_NAME: str = Field(default="text-embedding-ada-002", description="嵌入模型名称")

    # ========== 性能配置 ==========
    NUM_THREADS: int = Field(default_factory=lambda: max(1, os.cpu_count() - 1), description="线程数")
    CPU_NUM: int = Field(default_factory=lambda: max(1, os.cpu_count() - 1), description="CPU数量")

    # ========== LangChain配置 ==========
    LANGCHAIN_ROOT_PATH: str = Field(default=str(BASE_DIR / "app/langchain"), description="LangChain根路径")

    # ========== 监控配置 ==========
    ENABLE_METRICS: bool = Field(default=False, description="启用指标收集")
    METRICS_PORT: int = Field(default=9090, description="指标端口")

    # ========== 限流配置 ==========
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="启用限流")
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="限流请求数")
    RATE_LIMIT_WINDOW: int = Field(default=60, description="限流时间窗口（秒）")

    # ========== JWT配置优化 ==========
    # 兼容原有命名
    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        """访问令牌过期时间（分钟）"""
        return self.JWT_EXPIRE_HOURS * 60

    @property
    def REFRESH_TOKEN_EXPIRE_DAYS(self) -> int:
        """刷新令牌过期时间（天）"""
        return self.JWT_REFRESH_DAYS

    @property
    def ALGORITHM(self) -> str:
        """JWT算法"""
        return self.JWT_ALGORITHM

    # Pydantic配置
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore',
        validate_assignment=True,
        use_enum_values=True
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 创建必要的目录
        self._create_directories()

    def _create_directories(self):
        """创建必要的目录"""
        directories = [
            self.LOG_PATH,
            Path(self.LANGCHAIN_ROOT_PATH)
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    @property
    def uvicorn_config(self) -> dict:
        """获取Uvicorn配置"""
        config = {
            "host": self.HOST,
            "port": self.PORT,
            "reload": self.DEBUG,
            "log_level": self.LOG_LEVEL.lower(),
            "access_log": self.DEBUG,
        }

        if self.DEBUG:
            config.update({
                "reload_dirs": ["app"],
                "reload_includes": ["*.py"],
                "reload_excludes": ["*.pyc", "__pycache__"]
            })
        else:
            config["workers"] = self.WORKERS

        return config

    def get_database_config(self) -> dict:
        """获取数据库配置"""
        return {
            "pool_size": self.DB_POOL_SIZE,
            "max_overflow": self.DB_POOL_OVERFLOW,
            "pool_timeout": self.DB_POOL_TIMEOUT,
            "pool_recycle": self.DB_POOL_RECYCLE,
            "echo": self.DB_ECHO and self.DEBUG
        }

    def get_redis_config(self) -> dict:
        """获取Redis配置"""
        return {
            "host": self.REDIS_HOST,
            "port": self.REDIS_PORT,
            "db": self.REDIS_DB,
            "password": self.REDIS_PASSWORD,
            "max_connections": self.REDIS_MAX_CONNECTIONS,
            "socket_timeout": self.REDIS_TIMEOUT,
            "socket_connect_timeout": self.REDIS_TIMEOUT,
            "decode_responses": True,
            "retry_on_timeout": True,
            "health_check_interval": 30
        }

    def model_dump_safe(self) -> dict:
        """安全导出配置（隐藏敏感信息）"""
        data = self.model_dump()
        sensitive_keys = [
            'POSTGRES_PASSWORD', 'JWT_SECRET_KEY', 'SECRET_KEY',
            'OPENAI_API_KEY', 'REDIS_PASSWORD'
        ]

        for key in sensitive_keys:
            if key in data and data[key]:
                data[key] = "***HIDDEN***"

        return data


def initialize_settings() -> Settings:
    """初始化设置"""
    try:
        settings = Settings()
        return settings
    except Exception as e:
        print(f"❌ 配置初始化失败: {e}")
        raise


# 全局设置实例
settings = initialize_settings()