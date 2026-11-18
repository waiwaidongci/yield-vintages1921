"""读数导入与受影响区间范围重建。

一次性切换语义：读数入库、旧区间撤销、新区间落账、班次良率汇总均在同一事务内完成，
提交前外部读到的始终是上一版结果。同批补读以 idempotency_key 去重，重试不重复入账；
processing 批次可在进程重启后由 recover_stale_batches 按 payload 重放恢复。
"""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select

from src.config.database import Session
from src.constants.enums import BATCH_COMPLETED, BATCH_FAILED, BATCH_PROCESSING
from src.models.entities import Device, ImportBatch, MeterReading, OutputInterval
from src.services.audit import log
from src.services.intervals import Reading, resolve_interval


def _mark_failed(batch_id: int, exc: Exception):
    """独立短事务标记失败，不触碰调用方事务。"""
    with Session() as db:
        fresh = db.get(ImportBatch, batch_id)
        if fresh and fresh.status == BATCH_PROCESSING:
            fresh.status = BATCH_FAILED
            fresh.error = str(exc)[:500]
            fresh.finished_at = datetime.now()
            log(db, fresh.idempotency_key, 'import.failed', None, str(exc)[:400])
            db.commit()


def _rebuild_device(db, device: Device, window_start: datetime, batch_id: int) -> dict:
    """仅重建 window_start 起的相邻区间；更早区间保持不动。"""
    # 行级串行化同设备并发补读（SQLite 方言自动忽略 FOR UPDATE）
    db.query(Device).filter(Device.id == device.id).with_for_update().first()

    anchor = db.scalar(
        select(MeterReading)
        .where(MeterReading.device_id == device.id, MeterReading.read_at < window_start)
        .order_by(MeterReading.read_at.desc(), MeterReading.id.desc())
        .limit(1)
    )
    window = list(db.scalars(
        select(MeterReading)
        .where(MeterReading.device_id == device.id, MeterReading.read_at >= window_start)
        .order_by(MeterReading.read_at.asc(), MeterReading.id.asc())
    ).all())

    # 按最终顺序撤销旧差额：锚点之后的旧区间全部删除，再落新差额
    delete_from = anchor.read_at if anchor else window_start
    db.query(OutputInterval).filter(
        OutputInterval.device_id == device.id,
        OutputInterval.started_at >= delete_from,
    ).delete(synchronize_session=False)

    chain = ([anchor] if anchor else []) + window
    created = 0
    for prev, nxt in zip(chain, chain[1:]):
        result = resolve_interval(
            Reading(
                read_at=prev.read_at, total_input=prev.total_input, total_good=prev.total_good,
                meter_changed=prev.meter_changed, handover_input=prev.handover_input,
                handover_good=prev.handover_good,
            ),
            Reading(
                read_at=nxt.read_at, total_input=nxt.total_input, total_good=nxt.total_good,
                meter_changed=nxt.meter_changed, handover_input=nxt.handover_input,
                handover_good=nxt.handover_good,
            ),
            capacity=device.counter_capacity,
            max_rate_per_sec=device.max_rate_per_sec,
            shifts=device.shifts,
        )
        db.add(OutputInterval(
            device_id=device.id,
            prev_reading_id=prev.id,
            next_reading_id=nxt.id,
            import_batch_id=batch_id,
            **result,
        ))
        created += 1

    return {'window_readings': len(window), 'intervals_rebuilt': created}


def process_batch(batch_id: int) -> ImportBatch:
    """幂等执行批次：completed 直接返回；processing 在独立事务内按 payload 重放。

    独立事务保证失败整笔回滚、不污染调用方会话；成功则读数/区间一次性提交切换。
    """
    with Session() as db:
        batch = db.get(ImportBatch, batch_id)
        if not batch:
            raise HTTPException(404, '导入批次不存在')
        if batch.status == BATCH_COMPLETED:
            return batch
        try:
            payload = batch.payload
            # device_code 允许位于负载顶层（单设备导入）或每条读数上（CSV 多设备）
            rows = []
            for r in payload['readings']:
                item = dict(r)
                item.setdefault('device_code', payload.get('device_code'))
                rows.append(item)
            device_codes = sorted({r['device_code'] for r in rows})
            if not device_codes or any(not code for code in device_codes):
                raise HTTPException(422, '存在未指定设备编码的读数行')
            devices = {d.code: d for d in db.query(Device).filter(Device.code.in_(device_codes)).all()}
            missing = sorted(set(device_codes) - set(devices))
            if missing:
                raise HTTPException(422, f"设备未登记: {', '.join(missing)}")

            # 按设备分组并校验时点唯一
            grouped: dict[str, list[dict]] = {}
            for r in rows:
                grouped.setdefault(r['device_code'], []).append(r)
            for code, group_rows in grouped.items():
                times = [r['read_at'] for r in group_rows]
                if len(set(times)) != len(times):
                    raise HTTPException(422, f'设备 {code} 的导入负载存在重复时点读数')

            rebuilt_total = 0
            for code, group_rows in grouped.items():
                device = devices[code]
                parsed = []
                for r in group_rows:
                    read_at = r['read_at'] if isinstance(r['read_at'], datetime) else datetime.fromisoformat(r['read_at'])
                    parsed.append((read_at, r))

                existing = {x.read_at: x for x in db.scalars(
                    select(MeterReading).where(
                        MeterReading.device_id == device.id,
                        MeterReading.read_at.in_([p[0] for p in parsed]),
                    )
                ).all()}

                for read_at, r in parsed:
                    if read_at in existing:
                        continue  # 重试重放：读数已存在，不重复入账
                    db.add(MeterReading(
                        device_id=device.id,
                        read_at=read_at,
                        total_input=int(r['total_input']),
                        total_good=int(r['total_good']),
                        meter_changed=bool(r.get('meter_changed', False)),
                        handover_input=r.get('handover_input'),
                        handover_good=r.get('handover_good'),
                        import_batch_id=batch.id,
                    ))
                db.flush()

                window_start = min(p[0] for p in parsed)
                stats = _rebuild_device(db, device, window_start, batch.id)
                rebuilt_total += stats['intervals_rebuilt']

            batch.status = BATCH_COMPLETED
            batch.error = None
            batch.finished_at = datetime.now()
            batch.device_count = len(grouped)
            batch.reading_count = len(payload['readings'])
            log(db, payload.get('actor', 'operator'), 'import.completed', batch.idempotency_key,
                f'{len(payload["readings"])}条读数，重建{rebuilt_total}个区间')
            db.commit()
            return db.get(ImportBatch, batch.id)
        except Exception as exc:
            db.rollback()  # 业务写入整笔回滚
            _mark_failed(batch.id, exc)
            raise


def register_batch(db, payload: dict, async_mode: bool = False) -> tuple[ImportBatch, bool]:
    """登记导入批次。返回 (批次, 是否首次创建)；completed 批次幂等返回。"""
    key = payload['idempotency_key']
    existing = db.query(ImportBatch).filter_by(idempotency_key=key).first()
    if existing:
        if existing.status == BATCH_COMPLETED:
            return existing, False  # 同批补读重试：不重复入账
        if existing.status == BATCH_FAILED:
            existing.status = BATCH_PROCESSING
            existing.error = None
            existing.payload = payload
            db.commit()
        return existing, False

    batch = ImportBatch(
        idempotency_key=key,
        payload=payload,
        reading_count=len(payload['readings']),
        async_mode=async_mode,
        status=BATCH_PROCESSING,
    )
    db.add(batch)
    log(db, payload.get('actor', 'operator'), 'import.accepted', key,
        f'{len(payload["readings"])}条读数入队')
    db.commit()
    db.refresh(batch)
    return batch, True


def import_readings(db, payload: dict, async_mode: bool = False) -> ImportBatch:
    """同步导入：登记后立即在独立事务重放，一次性切换读数与区间。"""
    batch, _created = register_batch(db, payload, async_mode)
    if batch.status == BATCH_COMPLETED:
        return batch
    return process_batch(batch.id)


def recover_stale_batches(db) -> list[int]:
    """核算中断恢复：重放所有停留在 processing 的批次。"""
    stale = db.scalars(
        select(ImportBatch).where(ImportBatch.status == BATCH_PROCESSING)
    ).all()
    recovered = [batch.id for batch in stale]
    db.commit()
    for batch_id in recovered:
        process_batch(batch_id)
    if recovered:
        with Session() as audit_db:
            log(audit_db, 'worker', 'import.recovered', None, f'恢复批次: {recovered}')
            audit_db.commit()
    return recovered
