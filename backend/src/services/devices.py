from fastapi import HTTPException

from src.constants.enums import DEFAULT_SHIFTS
from src.models.entities import Device
from src.services.audit import log


def list_devices(db):
    return db.query(Device).order_by(Device.id).all()


def create_device(db, actor: str, data: dict) -> Device:
    if db.query(Device).filter_by(code=data['code']).first():
        raise HTTPException(409, '设备编码已存在')
    shifts = data.get('shifts') or DEFAULT_SHIFTS
    obj = Device(
        code=data['code'],
        name=data['name'],
        counter_capacity=int(data['counter_capacity']),
        max_rate_per_sec=int(data['max_rate_per_sec']),
        shifts=shifts,
    )
    db.add(obj)
    log(db, actor, 'device.create', data['code'])
    db.commit()
    db.refresh(obj)
    return obj
