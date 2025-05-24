#!/usr/bin/env python
# -*- coding: utf-8 -*-
import uvicorn
from fastapi import FastAPI, Request, Response, Depends
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
    get_redoc_html
)
from uuid import uuid4
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import os
from app.core.database import SessionLocal
from app.core.log import logger
# 导入配置和数据库
from app.core.settings import settings
from app.core.database import engine, create_tables

# 导入路由 - 检查路由是否存在
try:
    from app.api.v1 import auth

    router_imported = True
except ImportError as e:
    logging.warning(f"无法导入auth路由: {e}")
    router_imported = False


class RequestIDMiddleware(BaseHTTPMiddleware):
    """请求ID中间件，为每个请求生成唯一ID"""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers['X-Request-ID'] = request_id
        return response


def get_request_id(request: Request) -> str:
    """获取请求ID"""
    return getattr(request.state, 'request_id', 'unknown')


def get_user_id(request: Request) -> dict:
    """获取用户ID（占位函数）"""
    return {"user_id": "anonymous"}


# 创建FastAPI应用实例
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    docs_url=None,  # 禁用默认文档URL
    redoc_url=None,  # 禁用默认ReDoc URL
    openapi_url="/api/openapi.json",  # 设置OpenAPI JSON路径
    swagger_ui_parameters={"defaultModelsExpandDepth": -1}
)

# 添加中间件
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
)

# 静态文件挂载（如果目录存在）
if os.path.exists("assets"):
    app.mount("/app/assets", StaticFiles(directory="app/assets"), name="assets")

# 注册路由
if router_imported:
    app.include_router(auth.router, prefix="/api/v1")
    logger.info("✅ 成功导入auth路由")
else:
    logger.warning("⚠️ auth路由未导入，某些API可能不可用")


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有HTTP请求"""
    start_time = time.time()

    # 获取请求ID
    request_id = getattr(request.state, 'request_id', 'unknown')

    # 记录请求开始
    logger.info(f"[{request_id}] {request.method} {request.url.path} - 开始处理")

    try:
        # 处理请求
        response = await call_next(request)

        # 计算请求处理时间
        process_time = time.time() - start_time

        # 记录请求完成
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"状态码: {response.status_code} - "
            f"耗时: {process_time:.3f}s"
        )

        return response

    except Exception as e:
        # 记录请求异常
        process_time = time.time() - start_time
        logger.error(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"异常: {str(e)} - "
            f"耗时: {process_time:.3f}s"
        )
        raise


# 应用启动事件
@app.on_event("startup")
async def startup():
    """应用启动时执行"""
    try:
        logger.info("🚀 应用启动中...")
        # 创建数据库表
        create_tables()

        logger.info(f"✅ 应用启动成功 - {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}")
        logger.info(f"🐛 调试模式: {settings.DEBUG}")
        logger.info(f"📖 API文档: http://localhost:{settings.PORT}/docs")
        logger.info(f"📚 ReDoc文档: http://localhost:{settings.PORT}/redoc")

    except Exception as e:
        logger.error(f"❌ 应用启动失败: {str(e)}")
        raise


# 应用关闭事件
@app.on_event("shutdown")
async def shutdown():
    """应用关闭时执行"""
    try:
        # 关闭数据库连接池
        engine.dispose()
        logger.info("🔌 数据库连接已关闭")
        logger.info("👋 应用已安全关闭")

    except Exception as e:
        logger.error(f"❌ 应用关闭时发生异常: {str(e)}")


# 健康检查端点
@app.get("/health",
         tags=["系统"],
         summary="健康检查",
         description="检查系统是否正常运行")
async def health_check(request: Request):
    """
    健康检查接口

    返回:
        dict: 包含系统状态的字典
    """
    request_id = get_request_id(request)

    try:
        # 检查数据库连接
        db = SessionLocal()

        return {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": settings.PROJECT_VERSION,
            "request_id": request_id,
            "database": {
                "status": "connected",
            },
            "environment": {
                "debug": settings.DEBUG,
            },
            "routes": {
                "auth_imported": router_imported,
                "total_routes": len(app.routes)
            }
        }

    except Exception as e:
        logger.error(f"[{request_id}] 健康检查失败: {str(e)}")
        return {
            "status": "unhealthy",
            "service": settings.PROJECT_NAME,
            "version": settings.PROJECT_VERSION,
            "request_id": request_id,
            "database": {
                "status": "disconnected",
                "error": str(e)
            },
            "environment": {
                "debug": settings.DEBUG,
            }
        }


# API信息端点
@app.get("/api/info",
         tags=["系统"],
         summary="API信息",
         description="获取API的基本信息和可用路由")
async def api_info():
    """获取API信息"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "description": settings.PROJECT_DESCRIPTION,
        "openapi_url": "/api/openapi.json",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "routes_count": len(app.routes),
        "debug_mode": settings.DEBUG
    }


# 自定义OpenAPI端点（调试用）
@app.get("/api/openapi.json", include_in_schema=False)
async def get_openapi():
    """获取OpenAPI规范"""
    try:
        from fastapi.openapi.utils import get_openapi
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        app.openapi_schema = openapi_schema
        return openapi_schema
    except Exception as e:
        logger.error(f"生成OpenAPI规范时出错: {str(e)}")
        return {"error": "Failed to generate OpenAPI schema", "detail": str(e)}


# 自定义文档页面
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """自定义Swagger UI页面"""
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json",  # 使用自定义OpenAPI路径
        title=app.title + " - API文档",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_ui_parameters={"defaultModelsExpandDepth": -1}
    )


@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    """Swagger UI OAuth2 重定向"""
    return get_swagger_ui_oauth2_redirect_html()


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    """ReDoc文档页面"""
    return get_redoc_html(
        openapi_url="/api/openapi.json",  # 使用自定义OpenAPI路径
        title=app.title + " - ReDoc文档",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js",
    )


# 根路径重定向到文档
@app.get("/", include_in_schema=False)
async def root():
    """根路径，提供导航信息"""
    return {
        "message": f"🎉 欢迎使用 {settings.PROJECT_NAME}",
        "version": settings.PROJECT_VERSION,
        "status": "运行中",
        "links": {
            "api_docs": "/docs",
            "redoc_docs": "/redoc",
            "openapi_spec": "/api/openapi.json",
            "health_check": "/health",
            "api_info": "/api/info"
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else 4  # 开发模式下使用单进程
    )