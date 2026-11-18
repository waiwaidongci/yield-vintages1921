from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException

from src.config.database import Session, database
from src.constants.enums import BATCH_COMPLETED
from src.models.entities import ImportBatch
from src.schemas.requests import ImportPayload
from src.services import queue
from src.services.csv_import import parse_csv
from src.services.importer import process_batch, recover_stale_batches, register_batch
from src.utils.serialize import row

router = APIRouter(tags=['读数导入'])


def _run(db, payload: dict, async_mode: bool) -> ImportBatch:
    batch, _created = register_batch(db, payload, async_mode)
    if batch.status == BATCH_COMPLETED:
        return batch
    if async_mode:
        queue.enqueue_job(batch.id)        # worker 消费；进程中断后 recover 重放
        return db.get(ImportBatch, batch.id)
    return process_batch(batch.id)         # 同步：独立事务一次性切换


@router.post('/readings/import')
def import_json(payload: ImportPayload, async_mode: bool = False, db=Depends(database)):
    # mode=json：datetime 等统一为 JSON 原生类型，便于批次 payload 落库与重放
    return row(_run(db, payload.model_dump(mode='json'), async_mode))


@router.post('/readings/import-csv')
async def import_csv(file: UploadFile = File(...),
                     idempotency_key: str | None = Form(None),
                     async_mode: bool = False,
                     actor: str = Form('operator'),
                     db=Depends(database)):
    payload = parse_csv(await file.read(), idempotency_key, actor)
    return row(_run(db, payload, async_mode))


@router.get('/imports/{batch_id}')
def get_import(batch_id: int, db=Depends(database)):
    batch = db.get(ImportBatch, batch_id)
    if not batch:
        raise HTTPException(404, '导入批次不存在')
    return row(batch)


@router.get('/imports')
def list_imports(db=Depends(database)):
    batches = db.query(ImportBatch).order_by(ImportBatch.id.desc()).limit(100).all()
    return [row(b) for b in batches]


@router.post('/imports/recover')
def trigger_recover():
    """手动触发核算中断恢复（worker 启动时也会自动执行一次）。"""
    with Session() as db:
        ids = recover_stale_batches(db)
    return {'recovered_batch_ids': ids}
