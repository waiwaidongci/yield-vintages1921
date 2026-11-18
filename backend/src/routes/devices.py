from fastapi import APIRouter, Depends

from src.config.database import database
from src.schemas.requests import DeviceIn
from src.services import queue
from src.services.devices import create_device, list_devices
from src.utils.serialize import row

router = APIRouter(tags=['设备'])


@router.get('/devices')
def get_devices(db=Depends(database)):
    return [row(d) for d in list_devices(db)]


@router.post('/devices', status_code=201)
def post_device(body: DeviceIn, db=Depends(database)):
    return row(create_device(db, 'operator', body.model_dump(exclude_none=True)))


@router.get('/queue/info')
def queue_info():
    return {'redis_configured': queue.ping(), 'depth': queue.queue_depth()}
