# 初始结构

SQLAlchemy 启动时（`Base.metadata.create_all`）创建以下业务表：

- `devices`：设备台账。`counter_capacity` 计数上限（回卷/换表基准），`max_rate_per_sec` 最大产速（件/秒），`shifts` 为班次窗口 JSON。
- `meter_readings`：带时点累计读数。`(device_id, read_at)` 唯一；`meter_changed/handover_input/handover_good` 描述换表首读数与旧表交接值。
- `output_intervals`：相邻读数还原出的差额区间。`(prev_reading_id, next_reading_id)` 唯一；`status` 为 confirmed/pending，pending 带 `reason_code`，不计入班次良率。
- `import_batches`：导入批次。`idempotency_key` 唯一保证同批补读重试不重复入账；`payload` 保存原始负载，processing 状态在崩溃后由 worker/启动钩子按负载重放恢复。
- `audit_logs`：设备登记、导入接受/完成/失败、中断恢复的操作留痕。

差额还原口径见 `backend/src/services/intervals.py`，待确认原因代码见 `backend/src/constants/enums.py`。
本地开发未设置 `DATABASE_URL` 时使用 SQLite（`backend/data/app.db`，不入 Git）；docker-compose 使用 MySQL 8。已有数据库升级需先备份，后续字段演进以独立迁移执行。
