#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uvicorn
import time
import socket
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4
from sqlalchemy import text

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
    get_redoc_html
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# 核心模块导入
from app.core.database import create_tables, init_database, close_async_engine, close_sync_engine
from app.core.log import logger
from app.core.settings import settings

# 异步 Redis 客户端导入
REDIS_AVAILABLE = False
try:
    from app.core.redis import (
        init_redis_client,
        close_redis_client,
        get_redis_client,
        async_redis_client_manager
    )

    REDIS_AVAILABLE = True
    logger.info("✅ 异步Redis模块导入成功")
except ImportError as e:
    logger.warning(f"⚠️ Redis模块导入失败: {e}，将跳过Redis相关功能")

# 路由导入处理
ROUTER_MODULES = []
# try:
from app.api.v1 import auth, tag, task

ROUTER_MODULES = [
    (auth.router, "认证", "auth"),
    (tag.router, "标签", "tag"),
    (task.router, "任务", "task")
]
logger.info("✅ 所有路由模块导入成功")


# except ImportError as e:
#     logger.warning(f"⚠️ 路由模块导入失败: {e}")


class RequestIDMiddleware:
    """请求ID中间件，为每个请求生成唯一ID"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request_id = str(uuid4())
            scope["state"] = getattr(scope, "state", {})
            scope["state"]["request_id"] = request_id

            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.append([b"x-request-id", request_id.encode()])
                    message["headers"] = headers
                await send(message)

            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)


class RequestLoggingMiddleware:
    """请求日志中间件"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        request_id = scope.get("state", {}).get("request_id", "unknown")
        method = scope["method"]
        path = scope["path"]

        # 跳过健康检查和静态文件的日志
        skip_paths = ["/health", "/assets", "/favicon.ico"]
        should_log = not any(path.startswith(skip_path) for skip_path in skip_paths)

        if should_log:
            logger.info(f"[{request_id}] {method} {path} - 开始处理")

        async def send_wrapper(message):
            if message["type"] == "http.response.start" and should_log:
                process_time = time.time() - start_time
                status_code = message["status"]
                logger.info(
                    f"[{request_id}] {method} {path} - "
                    f"状态码: {status_code} - 耗时: {process_time:.3f}s"
                )
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            if should_log:
                process_time = time.time() - start_time
                logger.error(
                    f"[{request_id}] {method} {path} - "
                    f"异常: {str(e)} - 耗时: {process_time:.3f}s"
                )
            raise


class SecurityHeadersMiddleware:
    """安全头中间件"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))

                # 添加安全头
                security_headers = [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"x-xss-protection", b"1; mode=block"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                ]

                if not settings.DEBUG:
                    security_headers.append((b"strict-transport-security", b"max-age=31536000; includeSubDomains"))

                headers.extend(security_headers)
                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_wrapper)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理（异步版本）"""
    startup_time = time.time()

    # 启动阶段
    try:
        logger.info("🚀 应用启动中...")

        # 1. 初始化异步数据库
        try:
            if await init_database():
                logger.info("✅ 异步数据库初始化完成")
            else:
                logger.warning("⚠️ 异步数据库初始化失败，尝试同步方式...")
                create_tables()
                logger.info("✅ 同步数据库表创建/检查完成")
        except Exception as e:
            logger.error(f"❌ 数据库初始化失败: {str(e)}")
            raise

        # 2. 初始化异步Redis客户端
        if REDIS_AVAILABLE:
            try:
                await init_redis_client()
                logger.info("✅ 异步Redis客户端初始化完成")

                if await async_redis_client_manager.health_check():
                    logger.info("✅ Redis连接健康检查通过")
                else:
                    logger.warning("⚠️ Redis连接健康检查失败，但不影响启动")

            except Exception as e:
                logger.error(f"❌ Redis初始化失败: {str(e)}")
                logger.warning("⚠️ 应用将在没有Redis缓存的情况下继续运行")
        else:
            logger.info("ℹ️ Redis功能未启用")

        logger.info(f"✅ 应用启动成功 - {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}")
        logger.info(f"🌍 环境: {settings.ENVIRONMENT}")
        logger.info(f"📖 API文档: http://{settings.HOST}:{settings.PORT}/docs")
        logger.info(f"⚡ 启动耗时: {time.time() - startup_time:.3f}s")

    except Exception as e:
        logger.error(f"❌ 应用启动失败: {str(e)}")
        raise

    # 应用运行期间
    yield

    # 关闭阶段
    try:
        shutdown_time = time.time()
        logger.info("🔄 应用关闭中...")

        # 关闭异步Redis连接
        if REDIS_AVAILABLE:
            try:
                await close_redis_client()
                logger.info("✅ 异步Redis连接已关闭")
            except Exception as e:
                logger.warning(f"⚠️ Redis关闭过程中出错: {str(e)}")

        # 关闭数据库连接
        try:
            await close_async_engine()
            close_sync_engine()
            logger.info("✅ 数据库连接已关闭")
        except Exception as e:
            logger.warning(f"⚠️ 数据库关闭过程中出错: {str(e)}")

        logger.info(f"👋 应用已安全关闭 - 关闭耗时: {time.time() - shutdown_time:.3f}s")

    except Exception as e:
        logger.error(f"❌ 应用关闭时发生异常: {str(e)}")


def get_request_id(request: Request) -> str:
    """获取请求ID"""
    return getattr(request.state, 'request_id', 'unknown')


# 全局异常处理器
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证异常"""
    request_id = get_request_id(request)
    logger.warning(f"[{request_id}] 请求验证失败: {exc.errors()}")

    error_details = []
    for error in exc.errors():
        error_details.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": 422,
            "message": "请求验证失败",
            "success": False,
            "data": {
                "validation_errors": error_details
            },
            "timestamp": time.time(),
            "request_id": request_id
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """处理HTTP异常"""
    request_id = get_request_id(request)

    if exc.status_code >= 500:
        logger.error(f"[{request_id}] 服务器错误: {exc.detail}")
    elif exc.status_code >= 400:
        logger.warning(f"[{request_id}] 客户端错误: {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "success": False,
            "data": None,
            "timestamp": time.time(),
            "request_id": request_id
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """处理一般异常"""
    request_id = get_request_id(request)
    logger.error(f"[{request_id}] 未处理的异常: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": "服务器内部错误" if not settings.DEBUG else str(exc),
            "success": False,
            "data": None,
            "timestamp": time.time(),
            "request_id": request_id
        }
    )


def get_local_ip():
    """获取本机IP地址"""
    try:
        # 连接到一个远程地址来获取本地IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        try:
            # 备用方法
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except Exception:
            return "127.0.0.1"


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例"""

    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.PROJECT_VERSION,
        docs_url=None,  # 使用自定义文档
        redoc_url=None,
        openapi_url="/api/openapi.json",
        swagger_ui_parameters={"defaultModelsExpandDepth": -1},
        lifespan=lifespan  # 使用异步生命周期管理
    )

    # 异常处理器
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    # 中间件（按加载顺序）
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=settings.ALLOWED_METHODS,
        allow_headers=settings.ALLOWED_HEADERS,
    )

    # 可信主机中间件（仅在生产环境且非调试模式下启用）
    if not settings.DEBUG and settings.is_production:
        # 获取本机IP地址
        local_ip = get_local_ip()

        trusted_hosts = [
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            local_ip,
            settings.HOST
        ]

        # 添加局域网IP段（可选）
        if local_ip.startswith("192.168."):
            trusted_hosts.append("192.168.*")
        elif local_ip.startswith("10."):
            trusted_hosts.append("10.*")
        elif local_ip.startswith("172."):
            trusted_hosts.append("172.*")

        logger.info(f"启用TrustedHostMiddleware，允许的主机: {trusted_hosts}")

        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=trusted_hosts
        )
    else:
        logger.info("开发模式：跳过TrustedHostMiddleware以允许所有主机访问")

    # 静态文件配置
    assets_path = Path("app/assets")
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")
        logger.info("✅ 静态文件服务已启用")

    # 路由注册
    if ROUTER_MODULES:
        logger.info("🔧 开始注册路由...")

        for router, name, prefix in ROUTER_MODULES:
            app.include_router(
                router,
                prefix="/api/v1",
                tags=[name]
            )
            logger.info(f"✅ {name}路由注册完成")

        logger.info("🎉 所有路由注册完成!")
    else:
        logger.warning("⚠️ 没有可用的API路由")

    return app


# 创建应用实例
app = create_app()


# === 基础 API 端点 ===

@app.get("/", include_in_schema=False)
async def root():
    """根路径重定向到文档"""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["系统监控"])
async def health_check(request: Request):
    """系统健康检查接口"""
    request_id = get_request_id(request)
    check_time = time.time()

    health_data = {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "environment": settings.ENVIRONMENT,
        "request_id": request_id,
        "timestamp": check_time,
        "checks": {}
    }

    # 数据库检查
    try:
        from app.core.database import AsyncSessionLocal
        db_start = time.time()

        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))

        db_time = time.time() - db_start
        health_data["checks"]["database"] = {
            "status": "healthy",
            "response_time": f"{db_time:.3f}s"
        }
    except Exception as e:
        logger.error(f"[{request_id}] 数据库健康检查失败: {str(e)}")
        health_data["status"] = "degraded"
        health_data["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Redis检查
    if REDIS_AVAILABLE:
        try:
            redis_start = time.time()
            redis_client = get_redis_client()
            await redis_client.ping()
            redis_time = time.time() - redis_start

            health_data["checks"]["redis"] = {
                "status": "healthy",
                "response_time": f"{redis_time:.3f}s"
            }
        except Exception as e:
            logger.error(f"[{request_id}] Redis健康检查失败: {str(e)}")
            health_data["status"] = "degraded"
            health_data["checks"]["redis"] = {
                "status": "unhealthy",
                "error": str(e)
            }
    else:
        health_data["checks"]["redis"] = {
            "status": "disabled",
            "message": "Redis功能未启用"
        }

    return health_data


# === 文档端点 ===

@app.get("/api/openapi.json", include_in_schema=False)
async def custom_openapi():
    """自定义OpenAPI规范生成"""
    if app.openapi_schema:
        return app.openapi_schema

    try:
        from fastapi.openapi.utils import get_openapi

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        app.openapi_schema = openapi_schema
        return openapi_schema

    except Exception as e:
        logger.error(f"生成OpenAPI规范失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate OpenAPI schema: {str(e)}"
        )


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    """自定义Swagger UI"""
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json",
        title=f"{app.title} - API文档",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )


@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    """Swagger UI OAuth2 重定向处理"""
    return get_swagger_ui_oauth2_redirect_html()


@app.get("/redoc", include_in_schema=False)
async def custom_redoc():
    """自定义ReDoc文档"""
    return get_redoc_html(
        openapi_url="/api/openapi.json",
        title=f"{app.title} - ReDoc文档",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js",
    )


# === 启动配置 ===

def get_network_info():
    """获取网络信息"""
    local_ip = get_local_ip()

    network_info = {
        "host": settings.HOST,
        "port": settings.PORT,
        "local_url": f"http://127.0.0.1:{settings.PORT}",
        "local_ip": local_ip,
        "network_url": f"http://{local_ip}:{settings.PORT}"
    }

    return network_info


def print_startup_info():
    """打印启动信息"""
    network_info = get_network_info()

    print(f"\n{'=' * 60}")
    print(f"🚀 {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}")
    print(f"{'=' * 60}")
    print(f"🌍 环境: {settings.ENVIRONMENT}")
    print(f"🐛 调试模式: {settings.DEBUG}")
    print(f"🔄 Redis支持: {'✅' if REDIS_AVAILABLE else '❌'}")
    print(f"🛡️  TrustedHost中间件: {'❌ (开发模式禁用)' if settings.DEBUG else '✅'}")
    print(f"\n🌐 访问地址:")
    print(f"   本地访问: {network_info['local_url']}")
    print(f"   局域网访问: {network_info['network_url']}")
    print(f"   绑定地址: {settings.HOST}:{settings.PORT}")
    print(f"\n📚 API文档:")
    print(f"   Swagger UI: {network_info['network_url']}/docs")
    print(f"   ReDoc: {network_info['network_url']}/redoc")
    print(f"   健康检查: {network_info['network_url']}/health")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    # 打印启动信息
    print_startup_info()

    # 获取Uvicorn配置
    uvicorn_config = settings.uvicorn_config
    uvicorn_config["app"] = "main:app"

    logger.info(f"🚀 启动服务器...")

    try:
        uvicorn.run(**uvicorn_config)
    except KeyboardInterrupt:
        logger.info("👋 服务器被用户中断")
    except Exception as e:
        logger.error(f"❌ 服务器启动失败: {e}")
        raise