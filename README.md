# Database Query Tool

A web-based intelligent database query tool for managing database connections,
viewing metadata, running SQL queries, generating SQL from natural language, and
exporting query results.

This project is based on `tyrchen/geektime-bootcamp-ai/w2/db_query` and extends
the query workflow with result export features.

## Features

- Database connection management for PostgreSQL and MySQL.
- Metadata browsing for tables, views, columns, primary keys, and row counts.
- Manual SQL query execution with result preview.
- Natural-language-to-SQL generation through OpenAI.
- Query history recording.
- Query result export to CSV and JSON.
- One-click `EXECUTE & EXPORT` workflow for running a query and immediately
  downloading the result.
- Query-success prompt that asks whether the latest result should be exported.

## Export Workflow

After running a query, the results card provides two direct export buttons:

- `EXPORT CSV`
- `EXPORT JSON`

The manual SQL toolbar also includes `EXECUTE & EXPORT`, a dropdown command with
two automated actions:

- Execute and export CSV
- Execute and export JSON

For normal `EXECUTE`, the UI prompts after a successful query:

```text
Export query result?
Need to export this query result as CSV or JSON?
```

CSV export escapes commas, quotes, and newlines. JSON export includes query
metadata plus rows:

- `sql`
- `rowCount`
- `executionTimeMs`
- `columns`
- `rows`
- `exportedAt`

## Project Structure

```text
.
├── backend/          # FastAPI backend
├── frontend/         # React + TypeScript + Vite frontend
├── Makefile          # Development shortcuts
└── README.md
```

## Requirements

- Python 3.12+
- Node.js 22+
- `uv` is supported by the Makefile, but a standard Python virtual environment
  also works.

## Backend Setup

Using `uv`:

```bash
cd backend
uv sync --extra dev
cp .env.example .env
```

Using `venv` and `pip`:

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
cp .env.example .env
```

Edit `backend/.env` and set:

```text
OPENAI_API_KEY=your-openai-api-key
```

For database connection management and manual SQL execution, this key is only
required because the backend settings load it at startup. Natural-language SQL
generation requires a real key.

Start the backend:

```bash
cd backend
.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open:

```text
http://127.0.0.1:5173/
```

The frontend defaults to:

```text
http://localhost:8000
```

Override it with `VITE_API_BASE_URL` if needed.

## Example MySQL Connection

Use a short database name in the `Database Name` field and put the full URL in
the `Connection URL` field.

```text
Database Name: fraud_app
Connection URL: mysql://root:Rzxmaxc@123@10.128.13.67:3306/fraud_app
```

Do not put the full `mysql://...` URL into the `Database Name` field.

## Development Commands

```bash
# View Makefile commands
make help

# Start backend
make dev-backend

# Start frontend
make dev-frontend

# Run all tests
make test

# Run lint checks
make lint
```

## Verification

Frontend export utility tests:

```bash
cd frontend
npm test -- --run src/utils/exportResult.test.ts
```

Frontend production build:

```bash
cd frontend
npm run build
```

Backend import check:

```bash
cd backend
OPENAI_API_KEY=not-used-for-import .venv/bin/python -c 'from app.main import app; print(app.title)'
```

## Notes

- `.env`, virtual environments, `node_modules`, and build outputs are ignored by
  git.
- `backend/.env.example` is committed as the environment template.
- SQLite metadata for saved database connections is stored under
  `~/.db_query/db_query.db` by default.
