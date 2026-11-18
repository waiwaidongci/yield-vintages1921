"""并发补读：两线程同时补不同时点，最终区间一致且无重复入账。"""
import threading
from datetime import datetime

from src.config.database import Session
from src.models.entities import MeterReading, OutputInterval
from src.services.importer import import_readings


def _r(ts, ti, tg):
    return {'read_at': datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').isoformat(),
            'total_input': ti, 'total_good': tg}


def test_concurrent_supplementary_imports(db, device):
    base = {'idempotency_key': 'c-base', 'device_code': 'T-01', 'actor': 't', 'readings': [
        _r('2026-11-18 08:00:00', 100, 95),
        _r('2026-11-18 10:00:00', 2500, 2380),
    ]}
    import_readings(db, base)
    db.commit()

    errors = []

    def worker(key, ts, ti, tg):
        try:
            with Session() as s:
                import_readings(s, {'idempotency_key': key, 'device_code': 'T-01', 'actor': 't',
                                    'readings': [_r(ts, ti, tg)]})
        except Exception as exc:  # 锁竞争失败也要记录，不允许静默丢账
            errors.append(exc)

    t1 = threading.Thread(target=worker, args=('c-fill-1', '2026-11-18 09:00:00', 1300, 1240))
    t2 = threading.Thread(target=worker, args=('c-fill-2', '2026-11-18 09:30:00', 1900, 1810))
    t1.start(); t2.start(); t1.join(); t2.join()
    assert not errors, errors

    db.expire_all()
    # 2 条基础读数 + 2 条补读 → 3 个相邻区间，差额守恒
    assert db.query(MeterReading).count() == 4
    intervals = db.query(OutputInterval).order_by(OutputInterval.started_at).all()
    assert len(intervals) == 3
    assert sum(iv.input_delta for iv in intervals) == 2400
    assert sum(iv.good_delta for iv in intervals) == 2285
