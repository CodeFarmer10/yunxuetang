# 数据导出功能 — 作业拆解与实施计划

## 一、作业原文

> 为"数据库查询工具"添加数据导出功能模块：
> - 导出格式支持：至少两种格式（CSV、JSON）
> - 自动化流程：使得"执行查询"和"导出结果"可以一键完成或通过一个简单的命令触发
> - 用户交互：查询后 AI 助手主动询问"需要将这次查询结果导出为 CSV 或 JSON 文件吗？"
>
> 提交物：更新后的项目代码 + 一份 `FEATURE_EXPORT.md`（本文档）

---

## 二、现有代码结构分析（切入点）

### 2.1 后端现有与导出相关的链路

| 层 | 文件 | 导出改造切入点 |
|---|---|---|
| API 路由 | [app/api/v1/queries.py](file:///d:/workspace/cqj/act/example/aiCoding/geektime-bootcamp-ai-master/w2/db_query/backend/app/api/v1/queries.py) | 新增 `GET /{name}/export?format=csv\|json` 导出端点 |
| 查询执行 | [app/services/query_wrapper.py](file:///d:/workspace/cqj/act/example/aiCoding/geektime-bootcamp-ai-master/w2/db_query/backend/app/services/query_wrapper.py) | `execute_query_with_service` 返回 `QueryResult(columns, rows, ...)`，可直接复用为导出数据源 |
| 数据模型 | [app/models/schemas.py](file:///d:/workspace/cqj/act/example/aiCoding/geektime-bootcamp-ai-master/w2/db_query/backend/app/models/schemas.py) | 新增 `ExportRequest` / `ExportFormat` 等 schema |

### 2.2 前端现有与导出相关的链路

| 层 | 文件 | 导出改造切入点 |
|---|---|---|
| 查询执行页 | [pages/queries/execute.tsx](file:///d:/workspace/cqj/act/example/aiCoding/geektime-bootcamp-ai-master/w2/db_query/frontend/src/pages/queries/execute.tsx) | 在"查询结果"卡片区域新增导出按钮（CSV / JSON） |
| 结果表格 | [components/ResultTable.tsx](file:///d:/workspace/cqj/act/example/aiCoding/geektime-bootcamp-ai-master/w2/db_query/frontend/src/components/ResultTable.tsx) | 结果区域可增加导出操作入口 |
| API 客户端 | [services/api.ts](file:///d:/workspace/cqj/act/example/aiCoding/geektime-bootcamp-ai-master/w2/db_query/frontend/src/services/api.ts) | 新增 `exportQuery` 方法 |
| 类型定义 | [types/query.ts](file:///d:/workspace/cqj/act/example/aiCoding/geektime-bootcamp-ai-master/w2/db_query/frontend/src/types/query.ts) | 新增 `ExportFormat` 类型 |

---

## 三、功能设计

### 3.1 导出格式

| 格式 | MIME | 文件后缀 | 说明 |
|---|---|---|---|
| CSV | `text/csv` | `.csv` | 第一行为列名，后续为数据行，逗号分隔，含 BOM 以兼容 Excel 中文 |
| JSON | `application/json` | `.json` | 数组格式 `[{col: val, ...}, ...]`，带缩进美化 |

### 3.2 交互流程（前端）

```
用户执行 SQL 查询 → 查询结果展示
                    ↓
        结果卡片出现 [导出 CSV] [导出 JSON] 按钮
                    ↓
        点击导出 → 调用后端导出接口 → 浏览器下载文件
```

### 3.3 自动化流程（一键查询+导出）

作业要求"执行查询 + 导出结果一键完成"。设计两种实现方式：

**方式 A（推荐，前端按钮）：** 在查询执行页增加"查询并导出"按钮，点击后顺序执行查询 → 拿到结果 → 自动触发下载。

**方式 B（后端复合端点）：** 新增 `POST /{name}/query-and-export` 端点，传入 SQL + 导出格式，一次请求返回文件流。

两种方式都实现，前端按钮对应方式 A，后端端点对应方式 B（用于命令行/脚本调用）。

### 3.4 自然语言一键导出（NL → SQL → 执行 → 导出）

为满足“通过自然语言或简单界面操作触发导出”的交互要求，补充第三种自动化路径：

**方式 C（Natural Language 一键导出）：** 用户输入自然语言指令（例如“查询 app_judge_result 表有多少条数据 并将结果导出成csv格式”），后端完成：

1. 获取缓存元数据（用于 NL2SQL 上下文）
2. LLM 生成 SQL（仅 SELECT）
3. SQL 校验与自动补 LIMIT（安全兜底）
4. 执行查询
5. 直接返回文件流（CSV/JSON），浏览器自动下载

接口：

- `POST /api/v1/dbs/{name}/query/natural-and-export`
- 请求：
  - `prompt`: 自然语言指令
  - `format`（可选）: `csv` / `json`，不传则从 prompt 推断，默认 `csv`

---

## 四、原子化实施任务清单

### Task 1：后端 — 新增导出 Pydantic Schema

**文件：** `backend/app/models/schemas.py`

- 新增 `ExportFormat` 枚举：`CSV`、`JSON`
- 新增 `ExportRequest`：包含 `sql`（SQL 语句）、`format`（导出格式）
- 新增 `ExportResponse`：包含 `filename`（生成的文件名）

**验证：** 后端启动不报错，`/docs` 中能看到新 schema。

---

### Task 2：后端 — 新增导出服务

**新建文件：** `backend/app/services/export.py`

- 实现 `export_to_csv(columns, rows) -> str`：将查询结果转为 CSV 字符串
  - CSV 第一行为列名
  - 对含逗号/换行/引号的字段做转义
  - 写入 UTF-8 BOM（兼容 Excel 打开中文不乱码）
- 实现 `export_to_json(columns, rows) -> str`：将查询结果转为 JSON 字符串
  - 格式为 `[{"col1": val1, "col2": val2}, ...]`
  - `indent=2` 美化输出
- 实现 `generate_export_filename(db_name, format) -> str`：生成文件名（如 `mydb_20260729_153000.csv`）

**验证：** 编写单元测试 `tests/unit/test_export.py`，测试 CSV/JSON 生成逻辑。

---

### Task 3：后端 — 新增导出 API 端点

**文件：** `backend/app/api/v1/queries.py`

新增两个端点：

**端点 1：** `POST /{name}/export`（传入 SQL + 格式，直接返回文件）
- 输入：`ExportRequest`（sql + format）
- 处理：执行 SQL → 调用导出服务 → 返回 `StreamingResponse` 文件流
- Content-Type：`text/csv` 或 `application/json`
- Content-Disposition：`attachment; filename="xxx.csv"`

**端点 2：** `POST /{name}/query-and-export`（查询+导出一键完成）
- 输入：`QueryAndExportRequest`（sql + format）
- 处理：同端点 1，语义上强调"一键完成"
- 返回：文件流

**验证：**
- 用 `curl` 或 REST Client 测试：
  ```bash
  curl -X POST "http://localhost:8000/api/v1/dbs/mydb/export" \
    -H "Content-Type: application/json" \
    -d '{"sql": "SELECT * FROM users LIMIT 10", "format": "csv"}' \
    -o output.csv
  ```

---

### Task 4：前端 — 新增类型定义

**文件：** `frontend/src/types/query.ts`

- 新增 `ExportFormat` 类型：`"csv" | "json"`
- 新增 `ExportRequest` 接口：`{ sql: string; format: ExportFormat }`

**验证：** TypeScript 编译无报错。

---

### Task 5：前端 — API 客户端新增导出方法

**文件：** `frontend/src/services/api.ts`

- 新增 `exportData(databaseName, sql, format)` 方法
  - 调用后端 `POST /api/v1/dbs/{name}/export`
  - 响应类型为 `blob`
  - 触发浏览器下载（创建 `<a>` 标签 + `URL.createObjectURL`）

**验证：** 函数签名正确，TypeScript 类型检查通过。

---

### Task 6：前端 — 查询结果卡片增加导出按钮

**文件：** `frontend/src/pages/queries/execute.tsx`

在"Query Results"卡片中，`ResultTable` 上方新增 Button 组：
- `[导出 CSV]` 按钮：点击调用 `exportData(dbName, sql, "csv")`
- `[导出 JSON]` 按钮：点击调用 `exportData(dbName, sql, "json")`
- 按钮在 `result` 不为 null 时才显示
- 导出期间按钮显示 loading 状态

**验证：** 执行一条查询 → 结果出现后 → 点击导出按钮 → 浏览器下载对应格式文件 → 用 Excel/记事本打开验证内容正确。

---

### Task 7：前端 — 新增"查询并导出"一键按钮

**文件：** `frontend/src/pages/queries/execute.tsx`

在 SQL Editor 区域"Execute"按钮旁边，增加一个下拉合并按钮：
- 主按钮：`Execute`
- 下拉菜单：
  - `Execute & Export CSV`
  - `Execute & Export JSON`

点击后：先执行查询 → 拿到结果 → 自动触发对应格式的下载。

**验证：** 点击"Execute & Export CSV" → 查询执行 → 结果表格展示 → CSV 文件自动下载。

---

### Task 8：单元测试

**新建文件：** `backend/tests/unit/test_export.py`

- 测试 CSV 导出：验证列名、数据行、特殊字符转义、BOM
- 测试 JSON 导出：验证结构正确、缩进
- 测试导出文件名生成

**运行：** `uv run pytest tests/unit/test_export.py -v`

---

### Task 9：集成验证 + 文档

- 全链路测试：从前端输入 SQL → 执行 → 导出 CSV/JSON → 文件内容正确
- 补全本文档（FEATURE_EXPORT.md）
- 截图：查询结果页 + 导出按钮 + 下载后的文件内容

---

### Task 10：自然语言一键导出（方式 C）

**后端：**
- 新增 `POST /api/v1/dbs/{name}/query/natural-and-export`，实现 NL → SQL → 执行 → 导出（文件流返回）
- prompt 内包含 `csv/json/导出/下载` 等关键词时自动推断导出格式（默认 csv）

**前端：**
- 在 NATURAL LANGUAGE 输入区新增 `EXECUTE & EXPORT` 按钮，一键触发下载

**验证：**
- NATURAL LANGUAGE 输入：`查询 app_judge_result 表有多少条数据 并将结果导出成csv格式`
- 预期：浏览器下载 `.csv`，内容含列名与计数值

---

## 五、完成标准

| 检查项 | 标准 |
|---|---|
| CSV 导出 | 点击按钮后浏览器下载 `.csv` 文件，用 Excel 打开不乱码，列名和数据正确 |
| JSON 导出 | 点击按钮后浏览器下载 `.json` 文件，格式为 `[{col: val}, ...]`，可被 `JSON.parse` 解析 |
| 一键导出 | "Execute & Export CSV/JSON" 按钮可用，查询+导出一步完成 |
| 用户交互 | 查询结果出现后，导出按钮可见且可点击（符合"主动询问"的交互要求） |
| 自然语言一键导出 | NATURAL LANGUAGE 输入“……并导出 csv/json”可自动下载对应文件 |
| 后端 API | `POST /{name}/export` 可通过 curl 直接调用并返回文件流 |
| 测试 | `test_export.py` 所有用例通过 |
| 代码质量 | 无 lint 错误，无 type 错误 |

---

## 六、验证方法

### 6.1 后端 API 验证（curl）

```bash
# 导出 CSV
curl -X POST "http://localhost:8000/api/v1/dbs/mydb/export" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM users LIMIT 5", "format": "csv"}' \
  -o test_export.csv

# 导出 JSON
curl -X POST "http://localhost:8000/api/v1/dbs/mydb/export" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM users LIMIT 5", "format": "json"}' \
  -o test_export.json

# 自然语言一键导出（CSV）
curl -X POST "http://localhost:8000/api/v1/dbs/mydb/query/natural-and-export" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "查询 app_judge_result 表有多少条数据 并将结果导出成csv格式"}' \
  -o nl_export.csv

# 自然语言一键导出（JSON）
curl -X POST "http://localhost:8000/api/v1/dbs/mydb/query/natural-and-export" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "查询 app_judge_result 表有多少条数据 并导出 json"}' \
  -o nl_export.json
```

### 6.2 前端验证（浏览器）

1. 打开 `http://localhost:5173`
2. 选择一个已有数据库连接，进入查询页
3. 在 SQL 编辑器中输入 `SELECT * FROM xxx LIMIT 10`
4. 点击 Execute → 结果表格出现
5. 点击"导出 CSV"→ 浏览器下载文件 → 用 Excel 打开验证
6. 点击"导出 JSON"→ 浏览器下载文件 → 用文本编辑器打开验证
7. 点击"Execute & Export CSV"→ 查询+下载一步完成
8. 切到 NATURAL LANGUAGE，输入“查询 app_judge_result 表有多少条数据 并将结果导出成csv格式”→ 点击 `EXECUTE & EXPORT`→ 自动下载文件

### 6.3 单元测试验证

```bash
cd backend
uv run pytest tests/unit/test_export.py -v
```

---

## 七、文件改动清单

| 操作 | 文件 | 说明 |
|---|---|---|
| 新增 | `backend/app/services/export.py` | 导出服务（CSV/JSON 生成） |
| 修改 | `backend/app/models/schemas.py` | 新增 ExportFormat、ExportRequest、NaturalLanguageQueryAndExportRequest schema |
| 修改 | `backend/app/api/v1/queries.py` | 新增 `POST /{name}/export`、`POST /{name}/query-and-export`、`POST /{name}/query/natural-and-export` 端点 |
| 修改 | `frontend/src/types/query.ts` | 新增 ExportFormat 类型 |
| 修改 | `frontend/src/services/api.ts` | 新增 exportData、naturalQueryAndExport 方法 |
| 修改 | `frontend/src/pages/queries/execute.tsx` | 新增导出按钮 + 一键导出下拉菜单 |
| 修改 | `frontend/src/components/NaturalLanguageInput.tsx` | 新增 EXECUTE & EXPORT 入口 |
| 修改 | `frontend/src/pages/Home.tsx` | NATURAL LANGUAGE 支持一键执行并导出 |
| 新增 | `backend/tests/unit/test_export.py` | 导出服务单元测试 |
| 新增 | `backend/tests/unit/test_api_nl_query_and_export.py` | 自然语言一键导出 API 单元测试 |

---

## 八、实施顺序（建议）

1. Task 1 → Task 2 → Task 3 （后端 schema + 服务 + API，先跑通 curl）
2. Task 8 （后端单元测试，确保导出逻辑正确）
3. Task 4 → Task 5 （前端类型 + API 客户端）
4. Task 6 → Task 7 （前端 UI 按钮）
5. Task 9 （全链路验证 + 截图 + 文档）
