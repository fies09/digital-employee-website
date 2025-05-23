#!/bin/bash

echo "开始清理 Docker 环境..."

# 停止所有相关容器
echo "停止容器..."
docker stop digital_employee_api postgres-dev 2>/dev/null || true

# 删除容器
echo "删除容器..."
docker rm digital_employee_api postgres-dev 2>/dev/null || true

# 删除镜像
echo "删除镜像..."
docker rmi -f digital-employee-website-api 2>/dev/null || true
docker rmi -f digital-employee-website_middleware-middleware_postgres 2>/dev/null || true

# 使用compose清理
echo "使用 Docker Compose 清理..."
docker compose down -v --rmi all 2>/dev/null || true

# 清理系统
echo "清理未使用的资源..."
docker system prune -f

echo "清理完成！"
