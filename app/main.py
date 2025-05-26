import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
    get_redoc_html
)
from uuid import uuid4
import time
from pathlib import Path

# 核心模块导入
from app.core.database import SessionLocal, engine, create_tables
from app.core.log import logger
from app.core.settings import settings

# 路由导入处理
ROUTER_MODULES = []
try:
    from app.api.v1 import auth, tag, task

    ROUTER_MODULES = [
        (auth.router, "认证"),
        (tag.router, "标签"),
        (task.router, "任务")
    ]
    logger.info("✅ 所有路由模块导入成功")
except ImportError as e:
    logger.warning(f"⚠️ 路由模块导入失败: {e}")


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

        logger.info(f"[{request_id}] {method} {path} - 开始处理")

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
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
            process_time = time.time() - start_time
            logger.error(
                f"[{request_id}] {method} {path} - "
                f"异常: {str(e)} - 耗时: {process_time:.3f}s"
            )
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    try:
        logger.info("🚀 应用启动中...")
        create_tables()
        logger.info(f"✅ 应用启动成功 - {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}")
        logger.info(f"🐛 调试模式: {settings.DEBUG}")
        logger.info(f"📖 API文档: http://{settings.HOST}:{settings.PORT}/docs")
        logger.info(f"📚 ReDoc文档: http://{settings.HOST}:{settings.PORT}/redoc")
    except Exception as e:
        logger.error(f"❌ 应用启动失败: {str(e)}")
        raise

    # 应用运行期间
    yield

    # 关闭
    try:
        if engine:
            engine.dispose()
            logger.info("🔌 数据库连接已关闭")
        logger.info("👋 应用已安全关闭")
    except Exception as e:
        logger.error(f"❌ 应用关闭时发生异常: {str(e)}")


def get_request_id(request: Request) -> str:
    """获取请求ID"""
    return getattr(request.state, 'request_id', 'unknown')


def get_user_id(request: Request) -> dict:
    """获取用户ID（占位函数）"""
    return {"user_id": "anonymous"}


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
        lifespan=lifespan
    )

    # 添加中间件
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=settings.ALLOWED_METHODS,
        allow_headers=settings.ALLOWED_HEADERS,
    )

    # 静态文件配置
    assets_path = Path("app/assets")
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")
        logger.info("✅ 静态文件服务已启用")

    # 注册路由
    for router, name in ROUTER_MODULES:
        app.include_router(router, prefix="/api/v1", tags=[name])
        logger.info(f"✅ {name}路由已注册")

    if not ROUTER_MODULES:
        logger.warning("⚠️ 没有可用的API路由")

    return app


# 创建应用实例
app = create_app()


# === API 端点定义 ===

@app.get("/",
         include_in_schema=False,
         summary="根路径",
         description="应用根路径，重定向到API文档")
async def root():
    """根路径重定向到文档"""
    return RedirectResponse(url="/docs")


@app.get("/health",
         tags=["系统监控"],
         summary="健康检查",
         description="检查系统各组件运行状态",
         response_model=dict)
async def health_check(request: Request):
    """
    系统健康检查接口

    Returns:
        dict: 系统状态信息
    """
    request_id = get_request_id(request)

    health_data = {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "request_id": request_id,
        "timestamp": time.time(),
        "environment": {
            "debug": settings.DEBUG,
            "host": settings.HOST,
            "port": settings.PORT
        }
    }

    # 数据库连接检查
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        health_data["database"] = {"status": "connected"}
    except Exception as e:
        logger.error(f"[{request_id}] 数据库健康检查失败: {str(e)}")
        health_data["status"] = "degraded"
        health_data["database"] = {
            "status": "disconnected",
            "error": str(e)
        }

    # 路由状态检查
    health_data["routes"] = {
        "imported_count": len(ROUTER_MODULES),
        "total_routes": len(app.routes),
        "status": "loaded" if ROUTER_MODULES else "none"
    }

    return health_data


@app.get("/api/info",
         tags=["系统信息"],
         summary="API信息",
         description="获取API的详细信息和配置")
async def api_info():
    """获取API基本信息"""
    return {
        "application": {
            "name": settings.PROJECT_NAME,
            "version": settings.PROJECT_VERSION,
            "description": settings.PROJECT_DESCRIPTION,
            "debug_mode": settings.DEBUG
        },
        "endpoints": {
            "openapi_spec": "/api/openapi.json",
            "swagger_docs": "/docs",
            "redoc_docs": "/redoc",
            "health_check": "/health"
        },
        "statistics": {
            "total_routes": len(app.routes),
            "imported_modules": len(ROUTER_MODULES)
        }
    }


# === 文档相关端点 ===

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
        # 自定义OpenAPI配置
        openapi_schema["info"]["contact"] = {
            "name": "API Support",
            "email": "support@example.com"
        }
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
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,
            "displayRequestDuration": True,
            "filter": True,
            "showExtensions": True
        }
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


# === 开发环境启动配置 ===

if __name__ == "__main__":
    # 网络配置检查
    print(f"🔍 网络配置:")
    print(f"   绑定地址: {settings.HOST}")
    print(f"   端口: {settings.PORT}")

    # 获取本机所有IP地址
    import socket

    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
        print(f"   本机IP: {local_ip}")
        print(f"🌐 访问地址:")
        print(f"   本地: http://127.0.0.1:{settings.PORT}")
        print(f"   局域网: http://{local_ip}:{settings.PORT}")
    except Exception as e:
        print(f"   无法获取本机IP: {e}")

    uvicorn_config = {
        "app": "app.main:app",
        "host": "0.0.0.0",  # 强制绑定所有接口
        "port": settings.PORT,
        "reload": settings.DEBUG,
        "reload_dirs": ["app"] if settings.DEBUG else None,
        "log_level": "info" if settings.DEBUG else "warning",
        "access_log": settings.DEBUG,
    }

    if not settings.DEBUG:
        uvicorn_config["workers"] = 4

    logger.info(f"🚀 启动服务器...")
    uvicorn.run(**uvicorn_config)