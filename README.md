# Digital Employee Website

这是一个数字员工网站的后端服务。

## 安装

```bash
poetry install
```

## 运行

```bash
poetry run python -m uvicorn app.main:app --reload
``` 

## 数据库迁移

```bash
# 生成初始迁移文件
poetry run alembic revision --autogenerate -m "Initial migration"

# 执行迁移
poetry run alembic upgrade head
```
