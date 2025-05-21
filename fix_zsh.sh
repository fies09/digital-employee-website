#!/bin/bash

echo "🔧 正在修复 zsh 补全问题..."

# 创建个人补全目录
mkdir -p ~/.zsh/completions

# 创建简单的 docker-compose 补全文件
cat > ~/.zsh/completions/_docker-compose << 'INNER_EOF'
#compdef docker-compose
_docker-compose() {
    local commands=(
        'build:Build services'
        'up:Start containers'
        'down:Stop containers'
        'logs:View logs'
        'ps:List containers'
    )
    if (( CURRENT == 2 )); then
        _describe 'commands' commands
    fi
}
_docker-compose "$@"
INNER_EOF

# 备份 .zshrc
cp ~/.zshrc ~/.zshrc.backup.$(date +%Y%m%d_%H%M%S)

# 修复 .zshrc 中的补全配置
# 找到并替换补全相关的配置
sed -i.tmp '/autoload -Uz compinit/,/compinit/c\
# 修复后的补全配置\
typeset -U fpath\
fpath=(~/.zsh/completions $fpath)\
fpath=(${fpath:#/opt/homebrew/share/zsh/site-functions})\
[[ -d "/Users/fanyong/.docker/completions" ]] && fpath=(/Users/fanyong/.docker/completions $fpath)\
autoload -Uz compinit\
compinit -u >/dev/null 2>&1 || compinit >/dev/null 2>&1
' ~/.zshrc

# 清理补全缓存
rm -f ~/.zcompdump*

echo "✅ zsh 补全修复完成"
echo "🔄 请运行 'source ~/.zshrc' 重新加载配置"
