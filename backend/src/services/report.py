"""班次良率与待确认区间查询。良率只统计 confirmed 区间；pending 暂不计件。"""
from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy import select

from src.constants.enums import INTERVAL_CONFIRMED, INTERVAL_PENDING, REASONS
from src.models.entities import Device, MeterReading, OutputInterval


def _get_device(db, device_code: str | None) -> Device | None:
    if not device_code:
        return None
    device = db.query(Device).filter_by(code=device_code).first()
    if not device:
        raise HTTPException(404, '设备不存在')
    return device


def _interval_payload(db, iv: OutputInterval) -> dict:
    device = db.get(Device, iv.device_id)
    prev = db.get(MeterReading, iv.prev_reading_id) if iv.prev_reading_id else None
    nxt = db.get(MeterReading, iv.next_reading_id)
    return {
        'id': iv.id,
        'device_code': device.code if device else None,
        'device_name': device.name if device else None,
        'started_at': iv.started_at.isoformat(sep=' '),
        'ended_at': iv.ended_at.isoformat(sep=' '),
        'input_delta': iv.input_delta,
        'good_delta': iv.good_delta,
        'rollovers': iv.rollovers,
        'status': iv.status,
        'reason_code': iv.reason_code,
        'reason_text': REASONS.get(iv.reason_code) if iv.reason_code else None,
        'shift_name': iv.shift_name,
        'prev_input': prev.total_input if prev else None,
        'next_input': nxt.total_input if nxt else None,
        'prev_good': prev.total_good if prev else None,
        'next_good': nxt.total_good if nxt else None,
        'import_batch_id': iv.import_batch_id,
    }


def list_intervals(db, device_code: str | None = None, status: str | None = None):
    stmt = select(OutputInterval).order_by(OutputInterval.device_id, OutputInterval.started_at)
    if status:
        stmt = stmt.where(OutputInterval.status == status)
    rows = db.scalars(stmt).all()
    payload = [_interval_payload(db, iv) for iv in rows]
    if device_code:
        payload = [x for x in payload if x['device_code'] == device_code]
    return payload


def pending_intervals(db, device_code: str | None = None):
    return list_intervals(db, device_code, INTERVAL_PENDING)


def shift_yields(db, device_code: str | None = None):
    """按 设备×日历日×班次 汇总；pending 区间不参与良率，仅计数展示。"""
    device = _get_device(db, device_code)
    stmt = select(OutputInterval).order_by(OutputInterval.started_at)
    if device:
        stmt = stmt.where(OutputInterval.device_id == device.id)
    intervals = db.scalars(stmt).all()

    devices = {d.id: d for d in db.query(Device).all()}
    groups: dict[tuple, dict] = defaultdict(
        lambda: {'input_total': 0, 'good_total': 0, 'confirmed_intervals': 0, 'pending_intervals': 0}
    )
    for iv in intervals:
        dev = devices[iv.device_id]
        key = (dev.code, dev.name, iv.started_at.date().isoformat(),
               iv.shift_name or '跨班/未归属')
        if iv.status == INTERVAL_CONFIRMED:
            groups[key]['input_total'] += iv.input_delta
            groups[key]['good_total'] += iv.good_delta
            groups[key]['confirmed_intervals'] += 1
        else:
            groups[key]['pending_intervals'] += 1

    rows = []
    for (code, name, day, shift_name), agg in sorted(groups.items()):
        rate = round(agg['good_total'] * 100 / agg['input_total'], 2) if agg['input_total'] else None
        rows.append({
            'device_code': code,
            'device_name': name,
            'date': day,
            'shift_name': shift_name,
            'input_total': agg['input_total'],
            'good_total': agg['good_total'],
            'yield_rate': rate,
            'confirmed_intervals': agg['confirmed_intervals'],
            'pending_intervals': agg['pending_intervals'],
        })
    return rows


def overview(db):
    devices = db.query(Device).count()
    readings = db.query(MeterReading).count()
    confirmed = db.query(OutputInterval).filter_by(status=INTERVAL_CONFIRMED).count()
    pending = db.query(OutputInterval).filter_by(status=INTERVAL_PENDING).count()
    return {
        'device_count': devices,
        'reading_count': readings,
        'confirmed_interval_count': confirmed,
        'pending_interval_count': pending,
    }
