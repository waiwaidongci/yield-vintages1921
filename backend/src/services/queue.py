"""导入任务队列。配置了 Redis 时用 Redis List，未配置时降级为内存队列。"""
from src.config.settings import REDIS_URL

QUEUE_KEY = 'meter:import-jobs'
_redis = None
_memory_queue: list[str] = []


def _client():
    global _redis
    if _redis is None and REDIS_URL:
        import redis
        _redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    return _redis


def enqueue_job(batch_id: int) -> bool:
    """返回是否进入异步队列。"""
    client = _client()
    if client is None:
        _memory_queue.append(str(batch_id))
        return True
    client.rpush(QUEUE_KEY, str(batch_id))
    return True


def dequeue_job(timeout: int = 5):
    client = _client()
    if client is None:
        return _memory_queue.pop(0) if _memory_queue else None
    item = client.blpop(QUEUE_KEY, timeout=timeout)
    return item[1] if item else None


def queue_depth() -> int:
    client = _client()
    if client is None:
        return len(_memory_queue)
    return client.llen(QUEUE_KEY)


def ping() -> bool:
    client = _client()
    if client is None:
        return False
    try:
        client.ping()
        return True
    except Exception:
        return False
