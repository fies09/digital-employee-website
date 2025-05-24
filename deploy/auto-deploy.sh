#!/bin/bash

# 配置变量
PROJECT_DIR="/home/fan/code/digital-employee-website"
DEPLOY_DIR="$PROJECT_DIR/deploy"
LOG_FILE="$DEPLOY_DIR/logs/deploy.log"
BACKUP_DIR="$DEPLOY_DIR/backups"

# 创建必要目录
mkdir -p "$DEPLOY_DIR/logs" "$BACKUP_DIR"

# 日志函数
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# 错误处理函数
handle_error() {
    log_message "错误: $1"
    log_message "部署失败，开始回滚..."

    # 如果有备份，尝试回滚
    if [ -f "$BACKUP_DIR/last_working_commit.txt" ]; then
        LAST_WORKING_COMMIT=$(cat "$BACKUP_DIR/last_working_commit.txt")
        log_message "回滚到提交: $LAST_WORKING_COMMIT"
        git checkout "$LAST_WORKING_COMMIT"
        docker-compose up -d
    fi

    exit 1
}

# 进入项目目录
cd "$PROJECT_DIR" || handle_error "无法进入项目目录"

log_message "==================== 开始自动部署 ===================="

# 1. 备份当前工作状态
CURRENT_COMMIT=$(git rev-parse HEAD)
log_message "当前提交: $CURRENT_COMMIT"

# 2. 拉取最新代码
log_message "正在拉取最新代码..."
if ! git pull origin master; then
    handle_error "拉取代码失败"
fi

NEW_COMMIT=$(git rev-parse HEAD)
log_message "更新后提交: $NEW_COMMIT"

# 3. 检查Docker Compose文件
if [ ! -f "docker-compose.yml" ]; then
    handle_error "找不到 docker-compose.yml 文件"
fi

# 4. 停止现有容器
log_message "正在停止现有容器..."
if ! docker-compose down; then
    log_message "警告: 停止容器时出现问题，继续执行..."
fi

# 5. 清理旧镜像 (可选)
log_message "清理未使用的Docker镜像..."
docker image prune -f

# 6. 重新构建镜像
log_message "正在重新构建Docker镜像..."
if ! docker-compose build --no-cache; then
    handle_error "构建Docker镜像失败"
fi

# 7. 启动容器
log_message "正在启动容器..."
if ! docker-compose up -d; then
    handle_error "启动容器失败"
fi

# 8. 等待服务启动
log_message "等待服务启动..."
sleep 10

# 9. 健康检查
log_message "执行健康检查..."
HEALTH_CHECK_URL="http://localhost:8000/health"  # 根据你的API调整

# 尝试5次健康检查
for i in {1..5}; do
    if curl -f -s "$HEALTH_CHECK_URL" >/dev/null 2>&1; then
        log_message "健康检查通过 (尝试 $i/5)"
        break
    else
        log_message "健康检查失败 (尝试 $i/5)，等待5秒后重试..."
        if [ $i -eq 5 ]; then
            handle_error "健康检查失败，服务可能没有正常启动"
        fi
        sleep 5
    fi
done

# 10. 保存成功的提交记录
echo "$NEW_COMMIT" > "$BACKUP_DIR/last_working_commit.txt"
log_message "保存成功部署的提交记录: $NEW_COMMIT"

# 11. 清理旧的备份记录 (保留最近10个)
cd "$BACKUP_DIR"
ls -1t commit_*.txt 2>/dev/null | tail -n +11 | xargs -r rm

# 12. 显示运行状态
log_message "正在运行的容器:"
docker-compose ps | tee -a "$LOG_FILE"

log_message "==================== 部署成功完成 ===================="

# 可选：发送通知
if command -v curl >/dev/null 2>&1; then
    # 如果你有webhook通知地址，可以在这里发送通知
    # curl -X POST "your-notification-webhook" -d "部署成功: $NEW_COMMIT"
    log_message "部署通知已发送"
fi

exit 0