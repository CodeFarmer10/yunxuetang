# Database Query Tool 启动与开发指南

本项目是一个前后端分离的“数据库查询工具”：

- 后端：FastAPI（Python 3.12+），提供连接管理、元数据、SQL 执行、自然语言转 SQL（OpenAI 兼容接口）
- 前端：React + Vite + TypeScript（Refine + antd）

## 环境要求

- Windows 10/11
- Python：3.12+
- Node.js：建议 18+（推荐 LTS）
- c

## Windows 安装 Python（3.12+）

1. 安装方式建议：到 Python 官网下载 Windows x64 Installer 安装
2. 安装时务必勾选：Add python.exe to PATH
3. 验证：

```powershell
python --version
```

## Windows 安装 uv

方式 A（推荐，PowerShell）：

```powershell
iwr https://astral.sh/uv/install.ps1 -UseBasicParsing | iex
uv --version
```

方式 B（备选，用 pip 安装）：

```powershell
python -m pip install -U uv
uv --version
```

## 配置 LLM（DeepSeek / OpenAI 兼容）

后端自然语言转 SQL 功能依赖一个 OpenAI 兼容的 LLM 服务。

配置文件位置：

- `w2/db_query/backend/.env`

创建方式（在 backend 目录下执行）：

```powershell
copy .env.example .env
```

在 `.env` 中填写（示例：DeepSeek V4 Pro）：

```env
LLM_API_KEY=你的key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-pro
```

## 启动后端（FastAPI）

在一个 PowerShell 窗口执行：

```powershell
cd d:\workspace\cqj\act\example\aiCoding\geektime-bootcamp-ai-master\w2\db_query\backend

uv sync --extra dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

验证：

- 健康检查：`http://localhost:8000/health`
- API 文档：`http://localhost:8000/docs`

## 启动前端（React/Vite）

新开第二个 PowerShell 窗口执行：

```powershell
cd d:\workspace\cqj\act\example\aiCoding\geektime-bootcamp-ai-master\w2\db_query\frontend

npm install
copy .env.local.example .env.local
npm run dev
```

打开页面：

- `http://localhost:5173`

## 目录结构（后端）

- `backend/app/` - 应用代码
  - `main.py` - FastAPI 入口
  - `config.py` - Pydantic Settings 配置
  - `database.py` - 本工具自身的 SQLite 存储
  - `models/` - SQLModel 实体与 Schema
  - `services/` - 业务服务（含 NL2SQL）
  - `api/v1/` - REST API 路由
- `backend/alembic/` - 数据库迁移（SQLite）
- `backend/tests/` - 单元测试

## 开发约定

- Python：ruff + mypy + pytest（依赖在 `uv sync --extra dev` 一次性安装）
- 前端：eslint + vitest
