from fastapi.openapi.utils import get_openapi
from app.core.config import settings

def custom_openapi():
    if settings.DEBUG:
        return get_openapi(
            title=settings.PROJECT_NAME,
            version=settings.PROJECT_VERSION,
            description=settings.PROJECT_DESCRIPTION,
            routes=app.routes,
            tags=[
                {
                    "name": "认证",
                    "description": "用户认证相关的 API 接口",
                },
                {
                    "name": "健康检查",
                    "description": "系统健康检查相关的 API 接口",
                }
            ],
            servers=[
                {
                    "url": "http://localhost:8000",
                    "description": "本地开发环境"
                },
                {
                    "url": "https://api.example.com",
                    "description": "生产环境"
                }
            ],
            contact={
                "name": "技术支持",
                "url": "https://example.com/support",
                "email": "support@example.com"
            },
            license_info={
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT"
            }
        )
    return get_openapi(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        description=settings.PROJECT_DESCRIPTION,
        routes=app.routes
    ) 