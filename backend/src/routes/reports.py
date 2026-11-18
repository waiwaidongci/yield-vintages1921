from fastapi import APIRouter, Depends

from src.config.database import database
from src.models.entities import MeterReading
from src.services.report import list_intervals, pending_intervals, shift_yields, overview
from src.utils.serialize import row

router = APIRouter(tags=['核算查询'])


@router.get('/overview')
def get_overview(db=Depends(database)):
    return overview(db)


@router.get('/readings')
def get_readings(device_code: str | None = None, db=Depends(database)):
    from src.models.entities import Device
    q = db.query(MeterReading)
    if device_code:
        device = db.query(Device).filter_by(code=device_code).first()
        if not device:
            return []
        q = q.filter_by(device_id=device.id)
    items = q.order_by(MeterReading.device_id, MeterReading.read_at).all()
    out = []
    for r in items:
        data = row(r)
        device = db.get(Device, r.device_id)
        data['device_code'] = device.code if device else None
        out.append(data)
    return out


@router.get('/intervals')
def get_intervals(device_code: str | None = None, status: str | None = None, db=Depends(database)):
    return list_intervals(db, device_code, status)


@router.get('/intervals/pending')
def get_pending(device_code: str | None = None, db=Depends(database)):
    return pending_intervals(db, device_code)


@router.get('/shift-yields')
def get_shift_yields(device_code: str | None = None, db=Depends(database)):
    return shift_yields(db, device_code)
