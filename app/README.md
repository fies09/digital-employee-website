# 商户认证系统技术栈文档

## 1. 系统概述

本系统是基于FastAPI的商户认证系统，通过iframe集成到比邻系统内，实现商户自动注册和JWT鉴权功能。

## 2. 技术栈

### 2.1 核心技术
- **Python版本**: 3.11 (兼容性最强的稳定版本)
- **Web框架**: FastAPI 0.104+
- **数据库**: PostgreSQL 15
- **缓存**: Redis 7
- **认证**: JWT (PyJWT)
- **容器化**: Docker + Docker Compose
- **ASGI服务器**: Uvicorn

### 2.2 主要依赖包
```
fastapi>=0.104.1
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
sqlalchemy>=2.0.23
asyncpg>=0.29.0
redis>=5.0.1
PyJWT>=2.8.0
cryptography>=41.0.8
python-multipart>=0.0.6
python-dotenv>=1.0.0
alembic>=1.13.0
psycopg2-binary>=2.9.9
```

## 3. 项目结构

```
digital-employee-website/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI应用入口
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # 配置管理
│   │   ├── database.py         # 数据库连接
│   │   ├── redis.py           # Redis连接
│   │   ├── security.py        # JWT安全相关
│   │   └── middleware.py      # 中间件
│   ├── models/
│   │   ├── __init__.py
│   │   └── merchant.py        # 商户数据模型
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── merchant.py        # Pydantic模型
│   │   └── auth.py           # 认证相关模型
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py           # 依赖注入
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── auth.py       # 认证相关API
│   │       └── merchant.py   # 商户相关API
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py   # 认证服务
│   │   └── merchant_service.py # 商户服务
│   └── utils/
│       ├── __init__.py
│       └── bilim_api.py      # 比邻API集成
├── migrations/               # 数据库迁移文件
├── tests/                   # 测试文件
├── docker-compose.yml       # Docker编排文件
├── Dockerfile              # Python应用镜像
├── requirements.txt        # Python依赖
├── .env.example           # 环境变量示例
└── README.md
```

## 4. 使用流程   
cd ../api
复制.env.base为.env 配置需和deploy下的.env相对应
poetry install 安装依赖
执行poetry run alembic upgrade head 迁移数据库
poetry run python -m uvicorn app.main:app --reload 运行后端