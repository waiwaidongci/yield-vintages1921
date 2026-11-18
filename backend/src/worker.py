"""worker：启动恢复中断批次，随后消费导入队列。"""
import logging
import time
from pathlib import Path

from src.config.database import Session
from src.config.settings import HEARTBEAT_FILE
from src.services import queue
from src.services.importer import process_batch, recover_stale_batches


def main():
    logging.basicConfig(level=logging.INFO, format='[worker] %(asctime)s %(message)s')
    heartbeat = Path(HEARTBEAT_FILE)
    logging.info('启动：先恢复中断的导入批次')
    with Session() as db:
        recovered = recover_stale_batches(db)
    if recovered:
        logging.info('已恢复批次 %s', recovered)

    while True:
        heartbeat.write_text(str(time.time()))
        job = queue.dequeue_job(timeout=5)
        if not job:
            continue
        batch_id = int(job)
        try:
            batch = process_batch(batch_id)  # 内部独立事务，失败落 failed 不拖垮 worker
            logging.info('批次 %s 完成状态=%s', batch_id, batch.status)
        except Exception:
            logging.exception('批次 %s 处理失败，已落 failed 状态，可同键重试', batch_id)


if __name__ == '__main__':
    main()
