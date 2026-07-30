# [OPEN] MySQL 连接失败与 ASGI 异常排查记录

## 会话信息

- session_id: mysql-connection-1045
- 环境: Windows / FastAPI + uvicorn / aiomysql(PyMySQL)
- 症状:
  - 前端创建连接时报: `(1045, "Access denied for user 'root'@'10.12.103.30' (using password: YES)")`
  - 同时出现 `Exception in ASGI application` 但用户日志未完整

## 目标

1. 明确 1045 的根因（密码解析 / 账号权限 / 网络路径差异 / 驱动认证依赖）。
2. 保证后端 API `/api/v1/dbs/{name}` 创建连接稳定返回，不触发 ASGI 级异常堆栈。

## 待验证假设（将用运行时证据逐一证伪/证实）

H1. 后端未重启或仍在使用旧代码，导致密码未 URL 解码（`%40` 仍为字面量）。

H2. DBeaver 连接走了 SSH Tunnel/代理，实际出网 IP 与本机 `10.12.103.30` 不同；而本工具为直连，因此被 MySQL 端拒绝。

H3. 服务器存在多个 root@host 账号条目或鉴权插件差异（如 root@'%' 与 root@'10.12.%'），导致从 `10.12.103.30` 来的连接命中拒绝规则。

H4. 后端 ASGI 异常堆栈实际由其他逻辑错误触发（例如 schema/migration 不一致、异常未被捕获），误导为连接失败；需要完整 trace 确认异常源头。

## 证据收集清单

- uvicorn 完整 traceback（从 ERROR 行开始到最后一行）
- 触发请求的 API 路径、请求体（PUT /api/v1/dbs/{name} 的 body）
- DBeaver 连接配置截图或文字：是否启用 SSH Tunnel、Host 实际填的是什么、Driver 参数

## 当前状态

- [ ] 收集完整日志
- [ ] 最小化插桩定位 H1/H2/H3/H4
- [ ] 基于证据给出最小修复方案

