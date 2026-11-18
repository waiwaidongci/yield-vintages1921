# 车间累计读数差额计件台

设备只上报**累计投入**与**累计合格**两个计数器。系统导入带时点读数，按各设备的**计数上限**与**最大产速**还原相邻读数之间的差额；回卷存在多个解、缺换表交接、跨班缺边界读数的区间**暂不计件**，进入待确认并登记原因。

## 业务规则与核算口径

### 1. 差额还原（`backend/src/services/intervals.py`）
- **单调读数**：差额 = 后值 − 前值，回卷次数 0。
- **回卷（读数倒退）**：计数器在 `counter_capacity` 处归零，候选解 `delta = 后值 − 前值 + k×capacity（k≥1）`。
  以 `最大产速 × 区间秒数` 为产能上限裁剪候选：
  - 恰好一个可行解 → 按该解计件；
  - 多个可行解（回卷多解）→ `rewind_ambiguous` 待确认；
  - 零个可行解（全部超产能）→ `rate_exceeded` 待确认。
- **换表**：换表后首读数带 `meter_changed` 与旧表交接值；差额 =（旧表交接 − 前读数）+ 新表初读数。缺交接或交接值非法 → `missing_handover` 待确认。
- **跨班边界**：区间内部经过班次边界时刻、而边界时刻没有读数 → `missing_boundary` 待确认；边界恰好有读数时自然拆成两段、各自归班。
- 同刻多值、合格大于投入等异常 → `bad_interval` 待确认。
- 待确认原因判定优先级：bad_interval > missing_handover > rewind_ambiguous > rate_exceeded > missing_boundary。

### 2. 范围重建与一次性切换
- 每次导入按设备找到**最早新读数的前一条锚点读数**，仅撤销锚点之后的旧区间并重算；更早区间不受影响（“并发补读只重算受影响的前后区间”）。
- 读数入库、旧差额撤销、新差额落账、批次状态在**同一数据库事务**提交，提交前外部读到的始终是上一版结果；班次良率由 confirmed 区间实时汇总，随之一次性切换。

### 3. 幂等、异步与中断恢复
- 每个导入批次带 `idempotency_key`（数据库唯一）：同批补读重试直接返回已完成批次，**不重复入账**。
- 批次先落 `processing` 与原始 payload，再核算。异步模式经 Redis 队列（无 Redis 时降级内存队列）交 worker 消费。
- 进程崩溃后，worker 启动与后端启动钩子都会 `recover_stale_batches`，按 payload 重放所有停留 `processing` 的批次；失败批次落 `failed` 并整笔回滚业务写入，同键修正后可重试。

### 4. 班次良率
按 设备 × 日历日 × 班次 汇总：`良率 = Σ合格差额 ÷ Σ投入差额`，**只统计 confirmed 区间**；pending 区间不计入分子分母，仅计数并在待确认页展示原因文案。

## 快速启动

```sh
cp .env.example .env
docker compose up -d --build
docker compose exec -T backend python -m scripts.seed_demo
```
前端 http://localhost:18253 ，后端文档 http://localhost:19253/docs ，MySQL 宿主端口 17753。五服务 frontend/backend/worker/db/redis，均带真实 healthcheck。清空演示数据：`docker compose down -v --remove-orphans`。

本地无 Docker 时（SQLite + 内存队列）：

```sh
cd backend
python -m pip install -r requirements-dev.txt
SEED_DEMO=true PYTHONPATH=. python -m scripts.seed_demo
PYTHONPATH=. uvicorn src.main:app --port 19253      # 后端
PYTHONPATH=. python -m src.worker                    # 另一终端：worker
cd ../frontend && node dev-server.cjs               # 静态服务 + /api 代理 → :18080
```

## 页面与 API

页面（原生 ES modules，无构建）：业务总览、设备台账、读数导入（JSON 单条/批量 + 中文表头 CSV）、班次良率、待确认区间（含原因）、过程留痕。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/devices` | 设备台账；登记计数上限、最大产速、班次 |
| POST | `/readings/import` | JSON 导入，`?async_mode=true` 走队列 |
| POST | `/readings/import-csv` | CSV 导入（multipart） |
| GET | `/readings` `/intervals` `/intervals/pending` | 读数与区间查询，可按 `device_code` 过滤 |
| GET | `/shift-yields` | 班次良率（pending 不计件） |
| GET | `/imports` `/imports/{id}` | 批次状态与错误 |
| POST | `/imports/recover` | 手动触发中断恢复（启动时也自动执行） |
| GET | `/audits` `/overview` `/health` | 留痕、总览、健康检查 |

CSV 表头（中英文均可）：`设备编码,时点,累计投入,累计合格,换表,交接投入,交接合格`。

## 工程结构

- `backend/src/services/intervals.py` 差额还原纯算法（可独立单测）；`shifts.py` 班次窗口；`importer.py` 批次登记、范围重建、恢复；`queue.py` Redis/内存队列；`report.py` 良率汇总。
- 表：`devices`、`meter_readings`、`output_intervals`、`import_batches`、`audit_logs`（见 `backend/migrations/001_schema.md`）。
- 测试：`backend/tests`，23 个用例覆盖回卷单解/多解、换表、跨班、超速、范围重建、幂等重试、失败回滚、崩溃恢复、并发补读、队列与 HTTP API。运行：`cd backend && python -m pytest tests/ -q`。
- 时间按 Asia/Shanghai 朴素值存储与展示；前端 `frontend/dev-server.cjs` 仅用于本地联调，生产用 nginx 配置。

## 已知边界

- 单 worker 消费队列；同设备并发补读靠数据库行锁（`SELECT … FOR UPDATE`，MySQL 生效；SQLite 降级为库级写锁）串行化。
- 计数器回卷默认按整数圈处理；设备首条读数之前没有区间。
- 班次窗口随设备 JSON 配置，页面暂只提供默认三班（早/中/晚）。

MIT License。
