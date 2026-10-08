# PostgreSQL MCP 功能完善作业报告

## 1. 作业信息

- 项目：PostgreSQL MCP Server
- 目录：`w5/pg-mcp`
- 提交人：待填写
- 完成日期：2026-10-08
- Git Commit：提交代码后填写

## 2. 作业背景

项目已经实现了 SQL 生成、SQL 安全校验、数据库执行、结果验证、弹性组件和可观测性组件，但部分设计能力没有进入真实请求处理流程，导致实际行为与 PRD、设计文档和测试计划存在偏差。

本次作业重点解决以下问题：

1. 多数据库配置和安全控制未真正启用。
2. 限流、重试退避、指标和追踪模块未接入实际请求流程。
3. 响应模型存在重复方法，部分配置未使用，关键接线行为缺少测试。

## 3. 问题分析

### 3.1 多数据库执行链路不完整

原实现只创建一个数据库连接池。虽然启动代码中存在 `sql_executors` 字典，但 `QueryOrchestrator` 只接收主数据库的单个执行器。

请求指定数据库时，系统会读取目标数据库对应的 Schema，但执行 SQL 时仍固定使用主执行器。如果未来增加多个连接池，可能出现使用一个数据库的 Schema 生成 SQL、却在另一个数据库执行的问题。

### 3.2 安全策略未接入配置

`SQLValidator` 已经具备表黑名单、列黑名单和 EXPLAIN 校验能力，但服务器启动时将这些参数固定设置为：

```python
blocked_tables=None
blocked_columns=None
allow_explain=False
```

因此无法通过配置保护敏感表和敏感字段，也无法配置 EXPLAIN 策略。

### 3.3 弹性模块未进入请求链路

项目中已经存在限流器和熔断器，但原请求入口没有使用限流器。重试流程只覆盖部分 SQL 校验失败场景，`retry_delay` 和 `backoff_factor` 没有参与实际计算，数据库瞬时错误也不会重试。

### 3.4 可观测性模块未产生业务指标

Prometheus 指标对象和 HTTP 服务已经实现，但请求、LLM、数据库和安全校验流程没有更新相应计数器或直方图。

追踪模块也没有进入 MCP 请求上下文，无法在异步调用链中传播统一的请求 ID。

### 3.5 响应模型和测试问题

`QueryResponse` 中存在两个同名 `to_dict()` 方法，后一个定义会覆盖前一个定义，导致序列化规则不一致。

原测试数量较多，但以下行为缺少有效验证：

- 请求是否选择了正确的数据库执行器；
- 安全配置是否经过服务器启动流程传入 SQL 校验器；
- 限流是否会在真实请求入口返回结构化错误；
- 重试是否使用配置的退避时间；
- Prometheus 指标是否真正收到业务事件；
- 请求 ID 是否能在上下文中传播。

## 4. 实现内容

### 4.1 多数据库配置与执行器选择

在 `Settings` 中增加 `databases: list[DatabaseConfig]`，并保留原有单数据库配置作为兼容回退方案。

启动时为每个数据库分别创建：

- asyncpg 连接池；
- Schema 缓存条目；
- `SQLExecutor` 实例。

`QueryOrchestrator` 现在持有数据库名称到执行器的映射，并根据请求解析出的数据库名称选择对应执行器。

多数据库可通过以下环境变量配置：

```env
DATABASES=[{"name":"analytics","host":"db-a","user":"reader","password":"..."},{"name":"operations","host":"db-b","user":"reader","password":"..."}]
```

系统会校验数据库名称唯一性。未配置 `DATABASES` 时，继续使用原来的 `DATABASE_*` 单数据库配置。

### 4.2 表、列和 EXPLAIN 安全策略

新增配置：

```env
SECURITY_BLOCKED_TABLES=secrets,audit_log
SECURITY_BLOCKED_COLUMNS=users.password,users.ssn
SECURITY_ALLOW_EXPLAIN=false
```

服务器创建 `SQLValidator` 时会传入以上配置，使已有的 SQLGlot 安全校验逻辑在真实请求中生效。

原有安全措施继续保留：

- 只允许安全的只读查询；
- 拦截危险 PostgreSQL 函数；
- 使用只读事务；
- 设置安全的 `search_path`；
- 可选切换只读数据库角色；
- 限制执行时间和最大返回行数。

### 4.3 限流与结构化错误

将 `MultiRateLimiter` 接入查询入口和 LLM 调用流程，分别控制：

- 最大并发查询数；
- 最大并发 LLM 调用数。

新增配置：

```env
RESILIENCE_MAX_CONCURRENT_QUERIES=10
RESILIENCE_MAX_CONCURRENT_LLM_CALLS=5
RESILIENCE_RATE_LIMIT_TIMEOUT=1.0
```

请求等待限流槽位超时后，系统返回 `rate_limit_exceeded` 结构化错误，而不是无限等待或抛出未处理异常。

### 4.4 重试与指数退避

SQL 生成和数据库执行流程现在使用以下公式计算重试延迟：

```text
delay = retry_delay × backoff_factor ^ attempt
```

对应配置：

```env
RESILIENCE_MAX_RETRIES=3
RESILIENCE_RETRY_DELAY=1.0
RESILIENCE_BACKOFF_FACTOR=2.0
```

例如默认配置下，连续重试的等待时间为 1 秒、2 秒和 4 秒。

数据库执行仅对 `DatabaseError` 进行重试。所有 SQL 在执行前均已通过只读安全校验，并在只读事务中执行。

### 4.5 指标与请求追踪

请求处理链路现在会记录：

- 查询请求成功和失败数量；
- 查询总耗时；
- LLM 生成和结果验证调用次数；
- LLM 调用耗时；
- 数据库查询耗时；
- SQL 安全拒绝数量。

每次 MCP 查询都会创建请求上下文和唯一请求 ID，并在请求结束后恢复原上下文，避免并发请求之间互相污染。

### 4.6 模型与配置清理

- 删除 `QueryResponse` 中重复的 `to_dict()`。
- 统一响应序列化规则。
- 当 `tokens_used` 不可用时稳定返回 `0`。
- 接入 `ValidationConfig.max_question_length`。
- 接入 `ValidationConfig.min_confidence_score`，对低置信度结果记录警告。
- 修正日志格式默认值，使代码、README 和测试统一使用 `json`。

## 5. 主要修改文件

| 文件 | 修改内容 |
| --- | --- |
| `src/pg_mcp/config/settings.py` | 多数据库、安全、并发和限流配置 |
| `src/pg_mcp/server.py` | 多连接池、多执行器及横切组件装配 |
| `src/pg_mcp/services/orchestrator.py` | 执行器选择、限流、重试、指标和追踪 |
| `src/pg_mcp/models/query.py` | 修复重复的 `to_dict()` |
| `src/pg_mcp/models/errors.py` | 增加问题长度错误模型 |
| `src/pg_mcp/db/pool.py` | 修正超时异常兼容性和静态检查问题 |
| `src/pg_mcp/services/sql_generator.py` | 完善正则结果类型处理 |
| `.env.example` | 增加新配置示例 |
| `README.md` | 增加多数据库、安全和限流配置说明 |

## 6. 测试补充

新增和完善的测试覆盖以下场景：

1. 多数据库配置和数据库名称唯一性校验；
2. 表、列和 EXPLAIN 配置解析；
3. 请求选择目标数据库对应的执行器；
4. 查询并发限制返回结构化错误；
5. 数据库失败按照配置进行退避重试；
6. 服务器启动时正确装配多个数据库及安全策略；
7. MCP 查询入口的正常、非法和异常响应；
8. Prometheus 指标包装器收到业务事件；
9. 请求 ID 上下文传播和恢复；
10. `QueryResponse.to_dict()` 响应字段稳定性。

## 7. 验证结果

### 7.1 单元测试与覆盖率

执行命令：

```powershell
.venv\Scripts\python -m pytest tests/unit -q --cov=pg_mcp --cov-report=term
```

结果：

```text
265 passed
Total coverage: 80.88%
Required test coverage of 80.0% reached
```

### 7.2 Ruff

执行命令：

```powershell
.venv\Scripts\ruff check src tests
```

结果：

```text
All checks passed!
```

### 7.3 Mypy

执行命令：

```powershell
.venv\Scripts\mypy src
```

结果：

```text
Success: no issues found in 30 source files
```

### 7.4 差异检查

执行命令：

```powershell
git diff --check -- w5/pg-mcp
```

结果：未发现空白字符或补丁格式错误。

### 7.5 OpenAI 兼容服务接入

新增 `OPENAI_BASE_URL` 配置，并将其同时传入 SQL 生成器和结果校验器，避免两个
LLM 调用链路使用不同端点。API Key 校验调整为供应商无关的非空校验，不再假设
所有服务商的 Key 都以 `sk-` 开头；同时将 `max_tokens` 上限与示例配置中的
`32000` 对齐。

火山方舟 Coding Plan 配置示例：

```env
OPENAI_API_KEY=替换为专属密钥
OPENAI_BASE_URL=https://ark.cn-beijing.volces.com/api/coding/v3
OPENAI_MODEL=ark-code-latest
```

相关单元测试验证了环境变量读取、URL 规范化，以及 SQL 生成和结果校验两个客户端
均收到相同的自定义 Base URL。

由于主配置由多个嵌套 `BaseSettings` 组成，还增加了单层嵌套环境变量解析规则，
保证 `.env` 中原有的 `DATABASE_HOST`、`OPENAI_BASE_URL`、
`SECURITY_BLOCKED_TABLES` 等平铺变量能够正确装配到对应子配置。逗号分隔的安全
列表禁用自动 JSON 解码，继续兼容 `.env.example` 的既有格式。

stdio MCP 的标准输出专用于 JSON-RPC 协议消息，因此应用日志统一输出到 stderr。
该修复避免服务器关闭日志被客户端误解析为 JSON，并通过本地客户端完成了
`initialize -> list_tools -> shutdown` 的完整协议验证。

## 8. 未执行的验证

本次未运行依赖真实 PostgreSQL 和有效大模型供应商 API Key 的完整端到端测试。提交前如具备相应环境，可继续执行：

```powershell
.venv\Scripts\python -m pytest tests/integration tests/e2e -v
```

集成测试可能产生 OpenAI API 调用费用，应使用测试数据库和受控 API Key。

## 9. 提交建议

仅暂存本次作业目录：

```powershell
git add w5/pg-mcp
git diff --cached --stat
git diff --cached
```

建议提交信息：

```text
feat(pg-mcp): integrate multi-db security resilience and observability
```

提交完成后，将提交哈希补充到本报告“作业信息”部分，并附上以下材料：

- `git show --stat HEAD` 输出或截图；
- 单元测试和覆盖率截图；
- Ruff 与 Mypy 通过截图；
- Git Commit 或 Pull Request 链接。

## 10. 总结

本次修改没有重新实现已有模块，而是修复了设计能力与运行时请求链路之间的断层。多数据库、安全限制、限流、退避重试、指标和追踪现在均进入实际执行流程，并通过新增测试验证关键组件确实完成装配。响应模型得到统一，项目单元测试覆盖率达到既定门槛。
