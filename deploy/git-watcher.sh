#!/bin/bash

# 配置变量
PROJECT_DIR="/home/fan/code/digital-employee-website"
DEPLOY_DIR="$PROJECT_DIR/deploy"
LOG_FILE="$DEPLOY_DIR/logs/git-watcher.log"
PID_FILE="$DEPLOY_DIR/git-watcher.pid"

# 创建日志目录
mkdir -p "$DEPLOY_DIR/logs"

# 日志函数
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# 检查是否已经在运行
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        log_message "Git监听服务已经在运行中 (PID: $OLD_PID)"
        exit 1
    else
        rm -f "$PID_FILE"
    fi
fi

# 保存当前进程ID
echo $$ > "$PID_FILE"

# 进入项目目录
cd "$PROJECT_DIR" || {
    log_message "错误: 无法进入项目目录 $PROJECT_DIR"
    exit 1
}

log_message "开始监听Git远程仓库变化..."
log_message "项目目录: $PROJECT_DIR"
log_message "监听进程PID: $$"

# 获取初始的提交哈希
LAST_HASH=$(git rev-parse HEAD)
log_message "当前提交哈希: $LAST_HASH"

# 主循环
while true; do
    # 获取远程更新
    if ! git fetch origin master 2>/dev/null; then
        log_message "警告: 获取远程更新失败，将在下次重试"
        sleep 30
        continue
    fi

    # 获取远程最新提交哈希
    REMOTE_HASH=$(git rev-parse origin/master)

    # 检查是否有更新
    if [ "$LAST_HASH" != "$REMOTE_HASH" ]; then
        log_message "检测到远程仓库更新!"
        log_message "本地哈希: $LAST_HASH"
        log_message "远程哈希: $REMOTE_HASH"

        # 检查是否有app目录的变化
        CHANGED_FILES=$(git diff --name-only "$LAST_HASH" "$REMOTE_HASH")
        APP_CHANGED=$(echo "$CHANGED_FILES" | grep "^app/" | wc -l)

        if [ "$APP_CHANGED" -gt 0 ]; then
            log_message "检测到app目录有变化，开始自动部署..."
            log_message "变化的文件:"
            echo "$CHANGED_FILES" | grep "^app/" | while read file; do
                log_message "  - $file"
            done

            # 调用部署脚本
            if bash "$DEPLOY_DIR/auto-deploy.sh"; then
                log_message "自动部署成功完成!"
                LAST_HASH="$REMOTE_HASH"
            else
                log_message "错误: 自动部署失败"
            fi
        else
            log_message "检测到更新，但app目录无变化，跳过部署"
            # 更新本地代码但不重新部署
            git pull origin master
            LAST_HASH="$REMOTE_HASH"
        fi
    fi

    # 等待30秒后继续检查
    sleep 30
done