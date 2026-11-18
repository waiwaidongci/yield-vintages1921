"""服务层集成：范围重建、幂等重试、崩溃恢复、班次良率。"""
from datetime import datetime

import pytest
from fastapi import HTTPException

from src.constants.enums import BATCH_COMPLETED, BATCH_PROCESSING, INTERVAL_CONFIRMED
from src.models.entities import ImportBatch, MeterReading, OutputInterval
from src.services.importer import import_readings, recover_stale_batches, register_batch
from src.services.report import shift_yields, pending_intervals


def _payload(key, rows, code='T-01', actor='tester'):
    return {'idempotency_key': key, 'device_code': code, 'actor': actor, 'readings': rows}


def _r(ts, ti, tg, **kw):
    return {'read_at': datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').isoformat(),
            'total_input': ti, 'total_good': tg, **kw}


def test_import_builds_intervals_and_yields(db, device):
    payload = _payload('k-1', [
        _r('2026-11-18 08:00:00', 100, 95),
        _r('2026-11-18 09:00:00', 1300, 1240),
        _r('2026-11-18 10:00:00', 2500, 2380),
    ])
    batch = import_readings(db, payload)
    assert batch.status == BATCH_COMPLETED
    db.expire_all()
    assert db.query(OutputInterval).count() == 2
    assert all(iv.status == INTERVAL_CONFIRMED for iv in db.query(OutputInterval).all())

    yields = shift_yields(db)
    assert len(yields) == 1
    row = yields[0]
    assert row['input_total'] == 2400 and row['good_total'] == 2285
    assert row['yield_rate'] == round(2285 * 100 / 2400, 2)
    assert row['pending_intervals'] == 0


def test_scoped_recompute_only_affected_window(db, device):
    import_readings(db, _payload('k-base', [
        _r('2026-11-18 08:00:00', 100, 95),
        _r('2026-11-18 09:00:00', 1300, 1240),
        _r('2026-11-18 10:00:00', 2500, 2380),
    ]))
    db.expire_all()
    untouched_id = db.query(OutputInterval).filter(
        OutputInterval.ended_at == datetime(2026, 11, 18, 9, 0)).first().id

    # 并发补读：在 09:30 插入新读数，只影响 [09:00,10:00] 这个区间
    import_readings(db, _payload('k-fill', [
        _r('2026-11-18 09:30:00', 1900, 1810),
    ]))
    db.expire_all()
    assert db.query(OutputInterval).count() == 3
    still = db.get(OutputInterval, untouched_id)
    assert still is not None and still.input_delta == 1200  # 前段差额未被撤销
    new_pair = db.query(OutputInterval).order_by(OutputInterval.id).all()[-2:]
    assert [iv.input_delta for iv in new_pair] == [600, 600]


def test_same_batch_retry_is_idempotent(db, device):
    payload = _payload('k-idem', [
        _r('2026-11-18 08:00:00', 100, 95),
        _r('2026-11-18 09:00:00', 1300, 1240),
    ])
    first = import_readings(db, payload)
    second = import_readings(db, payload)  # 同批补读重试
    assert first.id == second.id
    db.expire_all()
    assert db.query(MeterReading).filter(MeterReading.import_batch_id == first.id).count() == 2
    assert db.query(OutputInterval).count() == 1


def test_pending_intervals_excluded_from_yield(db, device):
    import_readings(db, _payload('k-pending', [
        _r('2026-11-18 08:00:00', 100, 95),
        _r('2026-11-18 09:00:00', 1300, 1240),   # 正常区间
        _r('2026-11-18 09:05:00', 1600, 1520),  # 5 分钟 +300，产能 600，正常
        _r('2026-11-18 09:10:00', 1900, 1810),  # 正常
        _r('2026-11-18 09:11:00', 2200, 2090),  # 一分钟 +300，超产能 120 → 待确认
    ]))
    db.expire_all()
    pending = pending_intervals(db)
    assert len(pending) == 1 and pending[0]['reason_code'] == 'rate_exceeded'
    yields = shift_yields(db)
    # 良率只含前三个 confirmed 区间：(1200/1145)+(300/280)+(300/290)，pending 不参与
    morning = [r for r in yields if r['shift_name'] == '早班'][0]
    assert morning['input_total'] == 1800 and morning['good_total'] == 1715
    assert morning['pending_intervals'] == 0
    assert sum(r['pending_intervals'] for r in yields) == 1


def test_recover_stale_processing_batch(db, device):
    payload = _payload('k-stale', [
        _r('2026-11-18 08:00:00', 100, 95),
        _r('2026-11-18 09:00:00', 1300, 1240),
    ])
    batch, _ = register_batch(db, payload)
    # 模拟核算中断：批次停留 processing 且读数未入账
    assert batch.status == BATCH_PROCESSING
    db.commit()  # 让独立恢复事务可见
    assert db.query(MeterReading).count() == 0

    recovered = recover_stale_batches(db)
    db.expire_all()
    assert recovered == [batch.id]
    assert db.get(ImportBatch, batch.id).status == BATCH_COMPLETED
    assert db.query(OutputInterval).count() == 1

    # 再次恢复：没有遗留批次，不重复入账
    assert recover_stale_batches(db) == []
    db.expire_all()
    assert db.query(MeterReading).count() == 2


def test_failed_batch_retry_with_same_key(db, device):
    # 设备不存在 -> 失败
    bad = _payload('k-fail', [
        _r('2026-11-18 08:00:00', 1, 1),
        _r('2026-11-18 09:00:00', 2, 2),
    ], code='NO-SUCH')
    with pytest.raises(HTTPException):
        import_readings(db, bad)
    db.expire_all()
    failed = db.query(ImportBatch).filter_by(idempotency_key='k-fail').first()
    assert failed.status == 'failed' and failed.error
    assert db.query(MeterReading).count() == 0  # 失败整笔回滚，无读数残留

    # 改成存在的设备后同键重试（失败回滚后读数未入账，重放完整执行）
    bad['device_code'] = 'T-01'
    batch = import_readings(db, bad)
    db.expire_all()  # 独立事务已提交，丢弃本 session 的身份映射缓存
    assert batch.status == BATCH_COMPLETED
    assert db.query(MeterReading).count() == 2
    assert db.query(OutputInterval).count() == 1
