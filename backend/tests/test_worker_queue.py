"""worker 队列：无 Redis 时走内存队列，enqueue/dequeue/process 全链路。"""
from datetime import datetime

from src.constants.enums import BATCH_PROCESSING
from src.models.entities import OutputInterval
from src.services import queue
from src.services.importer import process_batch, register_batch


def test_memory_queue_job_roundtrip(db, device):
    payload = {
        'idempotency_key': 'queue-k-1', 'device_code': 'T-01', 'actor': 'tester',
        'readings': [
            {'read_at': datetime(2026, 11, 18, 8, 0).isoformat(), 'total_input': 100, 'total_good': 95},
            {'read_at': datetime(2026, 11, 18, 9, 0).isoformat(), 'total_input': 1300, 'total_good': 1240},
        ],
    }
    batch, _ = register_batch(db, payload, async_mode=True)
    db.commit()
    assert batch.status == BATCH_PROCESSING

    queue.enqueue_job(batch.id)
    assert queue.queue_depth() >= 1
    job = queue.dequeue_job(timeout=1)
    assert int(job) == batch.id

    done = process_batch(batch.id)
    db.expire_all()
    assert done.status == 'completed'
    assert db.query(OutputInterval).count() == 1


def test_empty_queue_returns_none():
    # 排空其他用例可能留下的内存任务
    while queue.dequeue_job(timeout=0):
        pass
    assert queue.dequeue_job(timeout=0) is None
