# 数据导出功能 — 实施结果报告

## 实施概览

| 项目 | 状态 |
|---|---|
| 实施日期 | 2026-07-29 |
| 改动文件数 | 11 个（新增 3 + 修改 8） |
| 单元测试 | 18 个（导出 16 + 自然语言一键导出 2），全部通过 |
| 测试命令 | `uv run pytest tests/unit/test_export.py tests/unit/test_api_nl_query_and_export.py -v` |

---

## 改动文件清单

| 操作 | 文件 | 说明 |
|---|---|---|
| 修改 | `backend/app/models/schemas.py` | 新增 `ExportFormatEnum`、`ExportRequest`、`NaturalLanguageQueryAndExportRequest` |
| 新增 | `backend/app/services/export.py` | 导出服务：CSV/JSON 生成 + 文件名生成 |
| 修改 | `backend/app/api/v1/queries.py` | 新增 `POST /{name}/export`、`POST /{name}/query-and-export`、`POST /{name}/query/natural-and-export` |
| 修改 | `frontend/src/types/query.ts` | 新增 `ExportFormat`、`ExportRequest` 类型 |
| 修改 | `frontend/src/services/api.ts` | 新增 `exportData()`、`naturalQueryAndExport()` |
| 修改 | `frontend/src/pages/queries/execute.tsx` | 新增导出按钮 + 一键导出下拉菜单 |
| 修改 | `frontend/src/components/NaturalLanguageInput.tsx` | NATURAL LANGUAGE 新增 `EXECUTE & EXPORT` 按钮 |
| 修改 | `frontend/src/pages/Home.tsx` | NATURAL LANGUAGE 支持一键执行并导出 |
| 新增 | `backend/tests/unit/test_export.py` | 16 个单元测试 |
| 新增 | `backend/tests/unit/test_api_nl_query_and_export.py` | 自然语言一键导出 API 单元测试 |

---

## 功能实现详情

### 1. 后端导出 API

**端点 1：`POST /api/v1/dbs/{name}/export`**

```json
// 请求
{
  "sql": "SELECT * FROM users LIMIT 10",
  "format": "csv"
}

// 响应：文件流下载
// Content-Type: text/csv; charset=utf-8-sig
// Content-Disposition: attachment; filename="mydb_20260729_153000.csv"
```

**端点 2：`POST /api/v1/dbs/{name}/query-and-export`**

功能与端点 1 一致，语义上强调"一键完成"。

**端点 3：`POST /api/v1/dbs/{name}/query/natural-and-export`**

自然语言一键导出（NL → SQL → 执行 → 导出）：

```json
// 请求
{
  "prompt": "查询 app_judge_result 表有多少条数据 并将结果导出成csv格式"
}

// 响应：文件流下载
// Content-Type: text/csv; charset=utf-8-sig 或 application/json; charset=utf-8
// Content-Disposition: attachment; filename="mydb_20260729_153000.csv"
```

### 2. CSV 导出特性

- 第一行为列名
- 数据行由 `csv.writer` 自动处理逗号/引号转义
- 响应编码为 `utf-8-sig`（带 BOM），Excel 打开中文不乱码
- NULL 值输出为空字符串

### 3. JSON 导出特性

- 数组格式：`[{col1: val1, col2: val2}, ...]`
- `indent=2` 美化输出
- `ensure_ascii=False`，中文正常显示
- 只包含列定义中的字段，多余字段不输出

### 4. 前端交互

**查询结果导出按钮：**
- 查询执行后，结果卡片右上角出现"导出 CSV"和"导出 JSON"按钮
- 点击后调用后端 `/export` 端点，浏览器自动下载文件

**一键查询并导出：**
- 主 Execute 按钮改为下拉菜单（Dropdown）
- 菜单项：
  - `Execute & Export CSV`：先执行查询展示结果，再自动下载 CSV
  - `Execute & Export JSON`：先执行查询展示结果，再自动下载 JSON

**自然语言一键导出：**
- NATURAL LANGUAGE 输入区增加 `EXECUTE & EXPORT` 按钮
- 输入自然语言指令（包含 csv/json 或 “导出/下载”等关键词）→ 点击按钮 → 自动下载文件

---

## 验证方法

### 后端 API 验证（curl）

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

### 前端验证（浏览器）

1. 打开 `http://localhost:5173`
2. 选择一个数据库连接，进入查询页
3. 输入 SQL → 点击 Execute 下拉 → 执行查询
4. 结果出现后，点击"导出 CSV"→ 浏览器下载文件 → 用 Excel 打开验证
5. 点击"导出 JSON"→ 浏览器下载文件 → 文本编辑器验证
6. 测试一键导出：下拉菜单选择"Execute & Export CSV"→ 查询结果展示 + 自动下载
7. 切到 NATURAL LANGUAGE，输入“查询 app_judge_result 表有多少条数据 并将结果导出成csv格式”→ 点击 `EXECUTE & EXPORT`→ 自动下载文件

### 单元测试验证

```bash
cd backend
uv run pytest tests/unit/test_export.py tests/unit/test_api_nl_query_and_export.py -v
# 预期：18 passed
```

---

## 测试结果

```
tests/unit/test_export.py::TestExportToCsv::test_basic_csv PASSED
tests/unit/test_export.py::TestExportToCsv::test_csv_null_values PASSED
tests/unit/test_export.py::TestExportToCsv::test_csv_special_characters PASSED
tests/unit/test_export.py::TestExportToCsv::test_csv_double_quote_escape PASSED
tests/unit/test_export.py::TestExportToCsv::test_csv_newline_handling PASSED
tests/unit/test_export.py::TestExportToCsv::test_csv_empty_rows PASSED
tests/unit/test_export.py::TestExportToCsv::test_csv_missing_column_in_row PASSED
tests/unit/test_export.py::TestExportToJson::test_basic_json PASSED
tests/unit/test_export.py::TestExportToJson::test_json_null_values PASSED
tests/unit/test_export.py::TestExportToJson::test_json_indent PASSED
tests/unit/test_export.py::TestExportToJson::test_json_chinese_text PASSED
tests/unit/test_export.py::TestExportToJson::test_json_empty_rows PASSED
tests/unit/test_export.py::TestExportToJson::test_json_extra_fields_excluded PASSED
tests/unit/test_export.py::TestGenerateExportFilename::test_csv_filename PASSED
tests/unit/test_export.py::TestGenerateExportFilename::test_json_filename PASSED
tests/unit/test_export.py::TestGenerateExportFilename::test_filename_timestamp_format PASSED
tests/unit/test_api_nl_query_and_export.py::TestNaturalLanguageQueryAndExport::test_export_csv_by_prompt PASSED
tests/unit/test_api_nl_query_and_export.py::TestNaturalLanguageQueryAndExport::test_export_json_by_prompt PASSED

============================= 18 passed in 1.00s ==============================
```

---

## 作业要求对照

| 作业要求 | 实现情况 |
|---|---|
| 导出格式支持至少两种 | CSV + JSON |
| 自动化流程（一键导出） | Execute 下拉菜单支持"Execute & Export CSV/JSON" |
| 用户交互（查询后导出） | 查询结果卡片右上角显示"导出 CSV"/"导出 JSON"按钮 |
| 用户交互（自然语言触发导出） | NATURAL LANGUAGE 支持“EXECUTE & EXPORT”，输入“……并导出 csv/json”自动下载 |
| 代码库理解与扩展 | 基于现有 `execute_query_with_service` 复用查询结果 |
| AI Agent 任务分解 | 拆分为 10 个原子化任务，逐步实施 |
| 提交物 | 更新后代码 + FEATURE_EXPORT.md（本文档） |
