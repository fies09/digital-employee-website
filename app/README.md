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

## 4. 数据库设计

### 4.1 商户表 (merchants)

```sql
CREATE TABLE merchants (
    id SERIAL PRIMARY KEY,
    merchant_id VARCHAR(50) UNIQUE NOT NULL,  -- 商户ID
    app_key VARCHAR(100),                     -- 应用key
    app_secret VARCHAR(200),                  -- 应用密钥(加密存储)
    callback_address VARCHAR(500),           -- 回调地址
    password VARCHAR(255),                   -- 密码(可为空)
    user_source VARCHAR(10) DEFAULT 'U01',  -- 用户来源 U01=比邻用户,U02=网页端注册
    is_active BOOLEAN DEFAULT TRUE,          -- 是否激活
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_merchants_merchant_id ON merchants(merchant_id);
CREATE INDEX idx_merchants_app_key ON merchants(app_key);
```

## 5. 核心代码实现

### 5.1 配置管理 (app/core/config.py)

```python
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
        env_file = "../.env"


settings = Settings()
```

### 5.2 数据库连接 (app/core/database.py)

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

### 5.3 商户模型 (app/models/merchant.py)

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from ..core.database import Base

class Merchant(Base):
    __tablename__ = "merchants"
    
    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(String(50), unique=True, nullable=False, index=True)
    app_key = Column(String(100))
    app_secret = Column(String(200))  # 加密存储
    callback_address = Column(String(500))
    password = Column(String(255))  # 可为空
    user_source = Column(String(10), default="U01")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

### 5.4 Pydantic模型 (app/schemas/merchant.py)

```python
from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime

class MerchantBase(BaseModel):
    merchant_id: str
    app_key: Optional[str] = None
    callback_address: Optional[str] = None
    user_source: str = "U01"

class MerchantCreate(MerchantBase):
    app_secret: Optional[str] = None
    password: Optional[str] = None

class MerchantRegister(BaseModel):
    app_key: str
    app_secret: str
    
    @validator('app_key', 'app_secret')
    def validate_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('不能为空')
        return v

class MerchantResponse(MerchantBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

### 5.5 JWT安全 (app/core/security.py)

```python
from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext
from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        merchant_id: str = payload.get("sub")
        if merchant_id is None:
            return None
        return merchant_id
    except jwt.PyJWTError:
        return None

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

### 5.6 认证API (app/api/v1/auth.py)

```python
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ...core.database import get_db
from ...core.security import create_access_token
from ...services.auth_service import AuthService
from ...schemas.merchant import MerchantRegister
from ...schemas.auth import Token

router = APIRouter(prefix="/auth", tags=["认证"])

@router.get("/", response_model=Token)
async def auto_login(
    merchantId: str = Query(..., description="商户ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    自动登录接口
    检查merchantId参数，如果没有则禁止访问
    """
    if not merchantId:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="缺少merchantId参数，禁止访问"
        )
    
    auth_service = AuthService(db)
    token = await auth_service.auto_login(merchantId)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败"
        )
    
    return {"access_token": token, "token_type": "bearer"}

@router.post("/register", response_model=Token)
async def auto_register(
    merchantId: str = Query(..., description="商户ID"),
    register_data: MerchantRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    自动注册接口
    """
    if not merchantId:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="缺少merchantId参数，禁止访问"
        )
    
    auth_service = AuthService(db)
    token = await auth_service.auto_register(merchantId, register_data)
    
    return {"access_token": token, "token_type": "bearer"}
```

### 5.7 认证服务 (app/services/auth_service.py)

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.merchant import Merchant
from ..schemas.merchant import MerchantRegister, MerchantCreate
from ..core.security import create_access_token, get_password_hash
from ..utils.bilin_api import BilinAPI
from typing import Optional

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.bilin_api = BilinAPI()
    
    async def get_merchant_by_id(self, merchant_id: str) -> Optional[Merchant]:
        """根据商户ID获取商户信息"""
        result = await self.db.execute(
            select(Merchant).where(Merchant.merchant_id == merchant_id)
        )
        return result.scalar_one_or_none()
    
    async def auto_login(self, merchant_id: str) -> Optional[str]:
        """自动登录"""
        # 1. 检查商户是否已注册
        merchant = await self.get_merchant_by_id(merchant_id)
        
        if merchant and merchant.is_active:
            # 已注册用户，直接生成token
            return create_access_token(data={"sub": merchant_id})
        
        return None
    
    async def auto_register(self, merchant_id: str, register_data: MerchantRegister) -> str:
        """自动注册"""
        # 1. 检查是否已注册
        existing_merchant = await self.get_merchant_by_id(merchant_id)
        if existing_merchant:
            raise ValueError("商户已注册")
        
        # 2. 验证比邻应用配置
        is_valid = await self.bilin_api.validate_app_config(
            register_data.app_key,
            register_data.app_secret
        )
        
        if not is_valid:
            raise ValueError("应用key或应用密钥验证失败")
        
        # 3. 创建商户记录
        merchant_data = MerchantCreate(
            merchant_id=merchant_id,
            app_key=register_data.app_key,
            app_secret=get_password_hash(register_data.app_secret),  # 加密存储
            user_source="U01"
        )
        
        merchant = Merchant(**merchant_data.dict())
        self.db.add(merchant)
        await self.db.commit()
        await self.db.refresh(merchant)
        
        # 4. 生成JWT token
        return create_access_token(data={"sub": merchant_id})
```

## 6. Docker配置

### 6.1 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制并安装Python依赖
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY .. .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 6.2 docker-compose.yml

```yaml
version: '3.8'

services:
  # PostgreSQL数据库
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: merchant_auth
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Redis缓存
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # 应用服务
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/merchant_auth
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - .:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  postgres_data:
  redis_data:
```

## 7. 中间件配置
### 7.1 CORS中间件 (app/core/middleware.py)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware

def setup_middleware(app: FastAPI):
    # CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应配置具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 会话中间件
    app.add_middleware(
        SessionMiddleware,
        secret_key="your-session-secret-key"
    )
    
    # 可信主机中间件
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # 生产环境应配置具体主机
    )
```

## 8. 部署说明
### 8.1 环境准备
1. 安装Docker和Docker Compose
2. 创建`.env`文件：

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/merchant_auth
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-very-secret-jwt-key-here
DEBUG=false
BILIN_BASE_URL=https://api.bilin.com
```

### 8.2 部署命令
```bash
# 构建并启动服务
docker-compose up -d --build
# 运行数据库迁移
docker-compose exec app alembic upgrade head
# 查看日志
docker-compose logs -f app
```

### 8.3 健康检查
- 应用健康检查: `http://localhost:8000/health`
- API文档: `http://localhost:8000/docs`
- 数据库连接检查: `docker-compose exec db pg_isready`
- Redis连接检查: `docker-compose exec redis redis-cli ping`

## 9. API使用说明
### 9.1 iframe集成示例
```html
<iframe 
    src="https://your-domain:8000/?merchantId=1912011111133792" 
    width="100%" 
    height="600">
</iframe>
```

### 9.2 认证流程
1. **自动登录**: `GET /api/v1/auth/?merchantId={merchantId}`
2. **自动注册**: `POST /api/v1/auth/register?merchantId={merchantId}`

## 10. 安全考虑
- JWT密钥使用强随机字符串
- 应用密钥加密存储
- 生产环境配置HTTPS
- 限制CORS允许的域名
- 实施API速率限制
- 数据库连接使用连接池
- Redis配置访问密码

## 11. 监控和日志
- 使用uvicorn的内置日志
- 集成Prometheus指标(可选)
- 配置ELK日志收集(可选)
- 健康检查端点监控

## 12. 使用流程   
cd ../api
复制.env.base为.env 配置需和deploy下的.env相对应
poetry install 安装依赖
执行poetry run alembic upgrade head 迁移数据库
poetry run python -m uvicorn app.main:app --reload 运行后端