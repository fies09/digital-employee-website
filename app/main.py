import uvicorn
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
    get_redoc_html
)
from uuid import uuid4
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import logging
import time

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging import log_stream_generator
from app.api.v1 import users, items
from utils.common import get_request_id, get_user_id

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers['X-Request-ID'] = request_id
        return response

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    docs_url=None,
    redoc_url=None
)


app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# 注册路由
app.include_router(users.router, prefix="/api/v1")
app.include_router(items.router, prefix="/api/v1")


# 中间件记录所有请求
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # 处理请求
    response = await call_next(request)

    # 计算请求处理时间
    process_time = time.time() - start_time

    # 记录请求信息
    logging.getLogger("app").info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.2f}s"
    )

    return response


# 应用启动和关闭事件
@app.on_event("startup")
async def startup():
    # 创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logging.getLogger("app").info("Application started")


@app.on_event("shutdown")
async def shutdown():
    # 关闭数据库连接
    await engine.dispose()

    logging.getLogger("app").info("Application shutdown")


# 健康检查端点
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# 日志流端点
@app.get("/logs/stream")
async def stream_logs():
    return StreamingResponse(
        log_stream_generator(),
        media_type="text/event-stream"
    )


@app.get("/")
async def site_root(request_id: str = Depends(get_request_id), user_id: dict = Depends(get_user_id)):
    return {"request_id": request_id, "user_id": user_id, "YZY": "AI KIT"}

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/assets/js/swagger-ui-bundle.js",
        swagger_css_url="/assets/css/swagger-ui.css",
    )


@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="/assets/js/redoc.standalone.js",
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, workers=4)
