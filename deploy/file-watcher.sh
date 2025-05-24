#!/bin/bash

# 配置变量
PROJECT_DIR="/home/fan/code/digital-employee-website"
DEPLOY_DIR="$PROJECT_DIR/deploy"
APP_DIR="$PROJECT_DIR/app"
LOG_FILE="$DEPLOY_DIR/logs/file-watcher.log"
PID_FILE="$DEPLOY_DIR/file-watcher.pid"

# 创建日志目录
mkdir -p "$DEPLOY_DIR/logs"

# 日志函数
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# 检查依赖
if ! command -v inotifywait >/dev/null 2>&1; then
    log_message "错误: 需要安装 inotify-tools"
    log_message "请运行: sudo apt-get install inotify-tools"
    exit 1
fi

# 检查是否已经在运行
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        log_message "文件监听服务已经在运行中 (PID: $OLD_PID)"
        exit 1
    else
        rm -f "$PID_FILE"
    fi
fi

# 保存当前进程ID
echo $$ > "$PID_FILE"

# 检查app目录是否存在
if [ ! -d "$APP_DIR" ]; then
    log_message "错误: app目录不存在 ($APP_DIR)"
    exit 1
fi

log_message "开始监听app目录文件变化..."
log_message "监听目录: $APP_DIR"
log_message "监听进程PID: $$"

# 防抖动变量
LAST_EVENT_TIME=0
DEBOUNCE_SECONDS=3

# 主监听循环
while true; do
    # 监听app目录的文件变化
    EVENT=$(inotifywait -r -e modify,create,delete,move \
        --format '%w%f %e' \
        "$APP_DIR" \
        --exclude '\.(git|__pycache__|\.pyc|\.pyo|\.log|\.tmp)' \
        2>/dev/null)

    if [ $? -eq 0 ]; then
        CURRENT_TIME=$(date +%s)
        FILE_PATH=$(echo "$EVENT" | cut -d' ' -f1)
        EVENT_TYPE=$(echo "$EVENT" | cut -d' ' -f2)

        # 防抖动处理
        if [ $((CURRENT_TIME - LAST_EVENT_TIME)) -lt $DEBOUNCE_SECONDS ]; then
            continue
        fi

        LAST_EVENT_TIME=$CURRENT_TIME

        log_message "检测到文件变化: $FILE_PATH ($EVENT_TYPE)"

        # 过滤掉临时文件和不需要的文件
        if [[ "$FILE_PATH" =~ \.(tmp|swp|swo|log)$ ]] || \
           [[ "$FILE_PATH" =~ __pycache__ ]] || \
           [[ "$FILE_PATH" =~ \.git/ ]]; then
            log_message "忽略临时文件: $FILE_PATH"
            continue
        fi

        log_message "文件变化触发自动部署..."

        # 等待一段时间确保文件写入完成
        sleep 2

        # 自动提交变更到Git (可选)
        cd "$PROJECT_DIR"
        if git status --porcelain | grep -q "^.M\|^A.\|^D.\|^??"; then
            log_message "检测到Git变更，自动提交..."
            git add app/
            git commit -m "Auto commit: $(date '+%Y-%m-%d %H:%M:%S') - $EVENT_TYPE $FILE_PATH"

            # 推送到远程仓库 (可选)
            if git push origin master; then
                log_message "代码已推送到远程仓库"
            else
                log_message "警告: 推送到远程仓库失败"
            fi
        fi

        # 执行本地部署
        if bash "$DEPLOY_DIR/auto-deploy.sh"; then
            log_message "自动部署成功完成!"
        else
            log_message "错误: 自动部署失败"
        fi

    else
        log_message "监听进程意外退出，正在重启..."
        sleep 5
    fi
done