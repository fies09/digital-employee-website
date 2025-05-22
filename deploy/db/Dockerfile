# 使用 PostgreSQL 16 基础镜像
FROM postgres:16

# 安装 pgvector
RUN apt-get update && \
    apt-get install -y postgresql-16-pgvector && \
    rm -rf /var/lib/apt/lists/*

# 创建初始化脚本目录
RUN mkdir -p /docker-entrypoint-initdb.d

# 复制初始化脚本
COPY init.sql /docker-entrypoint-initdb.d/