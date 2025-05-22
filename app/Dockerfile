# 使用轻量级 Ubuntu 22.04 镜像
FROM ubuntu:22.04

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    TZ=Asia/Shanghai \
    LANG=C.UTF-8

# 配置路径
ENV PATH="$POETRY_HOME/bin:$PATH"
WORKDIR /app

# 安装系统依赖和 Python 3.11
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        software-properties-common \
        gnupg2 \
        curl \
        ca-certificates \
        libxrender1 \
        libxext6 \
        fontconfig \
        tzdata \
    && ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && dpkg-reconfigure --frontend noninteractive tzdata \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update \
    && apt-get install -y python3.11 python3.11-venv python3.11-dev \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    # 安装 Poetry
    && curl -sSL https://install.python-poetry.org | python3 - --yes \
    # 清理缓存
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 配置国内镜像源
RUN poetry config repositories.aliyun https://mirrors.aliyun.com/pypi/simple/ \
    && poetry config repositories.tsinghua https://pypi.tuna.tsinghua.edu.cn/simple/ \
    && poetry config repositories.pypi https://pypi.org/simple/

# 复制应用代码
COPY . .

# 安装 Python 依赖
RUN poetry install --no-root --no-dev

# 暴露端口
EXPOSE 8000

# 启动应用
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
                                                                                                                                              