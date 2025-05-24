#!/bin/bash

# 配置变量
PROJECT_DIR="/home/fan/code/digital-employee-website"
DEPLOY_DIR="$PROJECT_DIR/deploy"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印彩色信息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    echo "自动部署管理脚本"
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  start-git        启动Git远程监听服务"
    echo "  start-file       启动本地文件监听服务"
    echo "  stop-git         停止Git远程监听服务"
    echo "  stop-file        停止本地文件监听服务"
    echo "  status           查看服务状态"
    echo "  logs             查看日志"
    echo "  deploy           手动执行部署"
    echo "  install          安装依赖和初始化"
    echo "  clean            清理日志和临时文件"
    echo "  help             显示此帮助信息"
    echo ""
}

# 检查服务状态
check_service_status() {
    local service_name=$1
    local pid_file="$DEPLOY_DIR/${service_name}.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            print_success "$service_name 正在运行 (PID: $pid)"
            return 0
        else
            print_warning "$service_name PID文件存在但进程已停止"
            rm -f "$pid_file"
            return 1
        fi
    else
        print_info "$service_name 未运行"
        return 1
    fi
}

# 启动Git监听服务
start_git_watcher() {
    print_info "启动Git远程监听服务..."

    if check_service_status "git-watcher" >/dev/null 2>&1; then
        print_warning "Git监听服务已经在运行中"
        return 1
    fi

    nohup bash "$DEPLOY_DIR/git-watcher.sh" >/dev/null 2>&1 &
    sleep 2

    if check_service_status "git-watcher" >/dev/null 2>&1; then
        print_success "Git远程监听服务启动成功"
    else
        print_error "Git远程监听服务启动失败"
    fi
}

# 启动文件监听服务
start_file_watcher() {
    print_info "启动本地文件监听服务..."

    if check_service_status "file-watcher" >/dev/null 2>&1; then
        print_warning "文件监听服务已经在运行中"
        return 1
    fi

    # 检查依赖
    if ! command -v inotifywait >/dev/null 2>&1; then
        print_error "需要安装 inotify-tools"
        print_info "请运行: sudo apt-get install inotify-tools"
        return 1
    fi

    nohup bash "$DEPLOY_DIR/file-watcher.sh" >/dev/null 2>&1 &
    sleep 2

    if check_service_status "file-watcher" >/dev/null 2>&1; then
        print_success "本地文件监听服务启动成功"
    else
        print_error "本地文件监听服务启动失败"
    fi
}

# 停止服务
stop_service() {
    local service_name=$1
    local pid_file="$DEPLOY_DIR/${service_name}.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            print_info "正在停止 $service_name (PID: $pid)..."
            kill "$pid"
            sleep 2

            if kill -0 "$pid" 2>/dev/null; then
                print_warning "进程仍在运行，强制终止..."
                kill -9 "$pid"
            fi

            rm -f "$pid_file"
            print_success "$service_name 已停止"
        else
            print_warning "$service_name 进程不存在，清理PID文件"
            rm -f "$pid_file"
        fi
    else
        print_info "$service_name 未运行"
    fi
}

# 显示服务状态
show_status() {
    print_info "=== 自动部署服务状态 ==="
    check_service_status "git-watcher"
    check_service_status "file-watcher"

    print_info ""
    print_info "=== Docker容器状态 ==="
    cd "$PROJECT_DIR"
    docker-compose ps
}

# 查看日志
show_logs() {
    local log_type=$1
    local log_dir="$DEPLOY_DIR/logs"

    if [ -z "$log_type" ]; then
        echo "可用的日志文件:"
        ls -la "$log_dir"/*.log 2>/dev/null || print_info "暂无日志文件"
        return
    fi

    case $log_type in
        "git")
            tail -f "$log_dir/git-watcher.log"
            ;;
        "file")
            tail -f "$log_dir/file-watcher.log"
            ;;
        "deploy")
            tail -f "$log_dir/deploy.log"
            ;;
        *)
            print_error "未知的日志类型: $log_type"
            print_info "可用类型: git, file, deploy"
            ;;
    esac
}

# 手动部署
manual_deploy() {
    print_info "开始手动部署..."
    bash "$DEPLOY_DIR/auto-deploy.sh"
}

# 安装依赖
install_dependencies() {
    print_info "安装系统依赖..."

    # 检查并安装inotify-tools
    if ! command -v inotifywait >/dev/null 2>&1; then
        print_info "安装 inotify-tools..."
        sudo apt-get update
        sudo apt-get install -y inotify-tools
    else
        print_success "inotify-tools 已安装"
    fi

    # 创建必要目录
    mkdir -p "$DEPLOY_DIR/logs" "$DEPLOY_DIR/backups"

    # 设置脚本执行权限
    chmod +x "$DEPLOY_DIR"/*.sh

    print_success "依赖安装和初始化完成"
}

# 清理文件
clean_files() {
    print_info "清理日志和临时文件..."

    # 清理日志文件 (保留最近的)
    find "$DEPLOY_DIR/logs" -name "*.log" -mtime +7 -delete 2>/dev/null

    # 清理旧的备份文件
    find "$DEPLOY_DIR/backups" -name "commit_*.txt" -mtime +30 -delete 2>/dev/null

    # 清理Docker
    docker system prune -f

    print_success "清理完成"
}

# 主逻辑
case $1 in
    "start-git")
        start_git_watcher
        ;;
    "start-file")
        start_file_watcher
        ;;
    "stop-git")
        stop_service "git-watcher"
        ;;
    "stop-file")
        stop_service "file-watcher"
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs $2
        ;;
    "deploy")
        manual_deploy
        ;;
    "install")
        install_dependencies
        ;;
    "clean")
        clean_files
        ;;
    "help"|"")
        show_help
        ;;
    *)
        print_error "未知命令: $1"
        show_help
        exit 1
        ;;
esac