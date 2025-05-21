#!/bin/bash

# 备份当前代理设置
BACKUP_ALL_PROXY=$all_proxy
BACKUP_NO_PROXY=$no_proxy

# 临时禁用代理
unset all_proxy ALL_PROXY http_proxy https_proxy HTTP_PROXY HTTPS_PROXY

echo "正在安装Python依赖..."

# 安装依赖
pip install --no-cache-dir -i https://pypi.org/simple/ --trusted-host pypi.org \
fastapi==0.104.1 \
"uvicorn[standard]==0.24.0" \
pydantic==2.5.0 \
pydantic-settings==2.1.0 \
sqlalchemy==2.0.23 \
asyncpg==0.29.0 \
alembic==1.13.0 \
redis==5.0.1 \
PyJWT==2.8.0 \
"passlib[bcrypt]==1.7.4" \
python-dotenv==1.0.0 \
httpx==0.25.2 \
psycopg2-binary==2.9.9 \
cryptography==41.0.8 \
python-multipart==0.0.6

# 恢复代理设置
if [ ! -z "$BACKUP_ALL_PROXY" ]; then
    export all_proxy=$BACKUP_ALL_PROXY
fi

if [ ! -z "$BACKUP_NO_PROXY" ]; then
    export no_proxy=$BACKUP_NO_PROXY
fi

echo "安装完成！代理设置已恢复。"
