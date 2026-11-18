from datetime import datetime

from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, JSON, UniqueConstraint, Index

from src.config.database import Base
from src.constants.enums import BATCH_PROCESSING, INTERVAL_CONFIRMED


class Device(Base):
    """设备台账：计数上限（回卷/换表基准）与最大产速（件/秒）。"""
    __tablename__ = 'devices'

    id = Column(Integer, primary_key=True)
    code = Column(String(60), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    counter_capacity = Column(BigInteger, nullable=False)          # 计数器计数上限（含 0..cap-1）
    max_rate_per_sec = Column(Integer, nullable=False)             # 最大产速，件/秒
    shifts = Column(JSON, nullable=False)                          # 班次定义列表
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class MeterReading(Base):
    """带时点的设备累计读数：累计投入 total_input / 累计合格 total_good。"""
    __tablename__ = 'meter_readings'
    __table_args__ = (
        UniqueConstraint('device_id', 'read_at', name='uq_reading_device_time'),
        Index('ix_reading_device_time', 'device_id', 'read_at'),
    )

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, nullable=False)
    read_at = Column(DateTime, nullable=False)
    total_input = Column(BigInteger, nullable=False)
    total_good = Column(BigInteger, nullable=False)
    meter_changed = Column(Boolean, nullable=False, default=False)          # 是否为换表后的首个读数
    handover_input = Column(BigInteger, nullable=True)                      # 旧表交接累计投入
    handover_good = Column(BigInteger, nullable=True)                       # 旧表交接累计合格
    import_batch_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class OutputInterval(Base):
    """相邻读数还原出的差额区间；pending 暂不计件。"""
    __tablename__ = 'output_intervals'
    __table_args__ = (
        UniqueConstraint('prev_reading_id', 'next_reading_id', name='uq_interval_pair'),
        Index('ix_interval_device_window', 'device_id', 'started_at', 'ended_at'),
    )

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, nullable=False)
    prev_reading_id = Column(Integer, nullable=True)      # 设备首条读数之前的区间为 NULL（不生成行，仅保留字段语义）
    next_reading_id = Column(Integer, nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=False)
    input_delta = Column(BigInteger, nullable=True)
    good_delta = Column(BigInteger, nullable=True)
    rollovers = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default=INTERVAL_CONFIRMED)
    reason_code = Column(String(30), nullable=True)
    shift_name = Column(String(30), nullable=True)        # 区间整体归属班次；跨班缺边界时为 NULL
    import_batch_id = Column(Integer, nullable=True)      # 最近一次重建该区间的批次
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class ImportBatch(Base):
    """导入批次：客户端幂等键 + processing 状态支撑崩溃恢复与同批重试。"""
    __tablename__ = 'import_batches'
    __table_args__ = (
        UniqueConstraint('idempotency_key', name='uq_import_idem'),
    )

    id = Column(Integer, primary_key=True)
    idempotency_key = Column(String(80), nullable=False)
    device_count = Column(Integer, nullable=False, default=0)
    reading_count = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default=BATCH_PROCESSING)
    error = Column(String(500), nullable=True)
    payload = Column(JSON, nullable=False)                       # 原始负载：崩溃后按它重放，同批重试不重复入账
    async_mode = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    finished_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    """核算动作留痕：导入、设备变更、恢复、重建。"""
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True)
    actor = Column(String(120), nullable=False, default='operator')
    action = Column(String(60), nullable=False)
    target = Column(String(160), nullable=True)
    detail = Column(String(500), nullable=True)
    at = Column(DateTime, default=datetime.now, nullable=False)
