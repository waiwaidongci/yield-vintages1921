from fastapi import APIRouter, Depends

from src.config.database import database
from src.models.entities import AuditLog
from src.utils.serialize import row

router = APIRouter(tags=['审计'])


@router.get('/audits')
def list_audits(db=Depends(database)):
    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(200).all()
    return [row(x) for x in logs]
