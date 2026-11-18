"""演示数据：自然键幂等，重复执行不覆盖既有修改。

场景设计（设备 CNT-01，计数上限 10000，最大产速 2 件/秒）：
- 普通单调区间；
- 回卷单解（9950 -> 0060，唯一还原 110）；
- 回卷多解（高产能设备在长区间里多解）-> 待确认；
- 完整换表交接 vs 缺交接 -> 后者待确认；
- 跨班边界缺边界读数 -> 待确认；
- 超速区间 -> 待确认。
"""
from datetime import datetime

from src.config.database import Base, Session, engine
from src.constants.enums import DEFAULT_SHIFTS
from src.models import entities  # noqa: F401  注册全部表
from src.models.entities import Device, ImportBatch
from src.services.importer import register_batch, process_batch

DEMO_DEVICES = [
    {'code': 'CNT-01', 'name': '冲压一号机', 'counter_capacity': 10000, 'max_rate_per_sec': 2},
    {'code': 'CNT-02', 'name': '卷绕二号机', 'counter_capacity': 100000, 'max_rate_per_sec': 50},
]

# 每台设备一批演示读数
DEMO_READINGS = {
    'CNT-01': [
        # 普通单调
        ('2026-11-18 08:00:00', 100, 95, False, None, None),
        ('2026-11-18 10:00:00', 1300, 1240, False, None, None),   # +1200 / +1145
        # 回卷单解：9950 -> 320（投入+370），3600 秒产能 7200，k=2 的 10370 超产能 → 唯一解
        ('2026-11-18 12:00:00', 9950, 9700, False, None, None),
        ('2026-11-18 13:00:00', 320, 58, False, None, None),
        # 完整换表：旧表交接 300/290，新表从 100/95 起
        ('2026-11-18 15:30:00', 300, 290, False, None, None),
        ('2026-11-18 15:31:00', 100, 95, True, 300, 290),
        # 缺交接换表 -> missing_handover
        ('2026-11-18 15:50:00', 500, 470, False, None, None),
        ('2026-11-18 15:51:00', 80, 70, True, None, None),
        # 跨班缺边界：15:55 -> 16:10 跨越 16:00 边界
        ('2026-11-18 15:55:00', 200, 190, False, None, None),
        ('2026-11-18 16:10:00', 900, 850, False, None, None),
        # 超速：60 秒内 +300，产能上限 120
        ('2026-11-18 17:00:00', 1000, 940, False, None, None),
        ('2026-11-18 17:01:00', 1300, 1230, False, None, None),
    ],
    'CNT-02': [
        ('2026-11-18 08:00:00', 5000, 4800, False, None, None),
        ('2026-11-18 09:00:00', 185000, 178000, False, None, None),  # 一小时 18 万，产能 18 万恰好可行
        # 两小时产能 36 万：20 万差额可行，为后续回卷铺垫
        ('2026-11-18 11:00:00', 385000, 370000, False, None, None),
        ('2026-11-18 13:00:00', 25000, 22000, False, None, None),
    ],
}


def seed():
    Base.metadata.create_all(engine)
    with Session() as db:
        for spec in DEMO_DEVICES:
            if not db.query(Device).filter_by(code=spec['code']).first():
                db.add(Device(shifts=DEFAULT_SHIFTS, **spec))
        db.commit()

        for code, rows in DEMO_READINGS.items():
            key = f'seed-{code}-v1'
            if db.query(ImportBatch).filter_by(idempotency_key=key).first():
                continue
            payload = {
                'idempotency_key': key,
                'device_code': code,
                'actor': 'seed',
                'readings': [
                    {
                        'read_at': datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').isoformat(),
                        'total_input': ti, 'total_good': tg,
                        'meter_changed': mc,
                        'handover_input': hi, 'handover_good': hg,
                    }
                    for ts, ti, tg, mc, hi, hg in rows
                ],
            }
            batch, _ = register_batch(db, payload)
            process_batch(batch.id)


if __name__ == '__main__':
    seed()
    print('seed 完成')
