# Digital Employee Website

这是一个数字员工网站的后端服务。

## 安装

```bash
poetry install
```

## 运行

# 开发环境（推荐）
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app --log-level info

# 生产环境
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --log-level warning


## 数据库迁移

```bash
# 生成初始迁移文件
poetry run alembic revision --autogenerate -m "Initial migration"

# 执行迁移
poetry run alembic upgrade head
```
