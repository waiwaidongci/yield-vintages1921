import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config.database import Base, engine, Session
from src.config.settings import CONFIG, REDIS_URL
from src.models import entities  # noqa: F401  注册全部表
from src.routes import audits, devices, imports, reports
from src.middlewares.errors import Errors
from src.middlewares.rate import RateLimit
from src.services.importer import recover_stale_batches


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    if os.getenv('SEED_DEMO') == 'true':
        try:
            from scripts.seed_demo import seed
            seed()
        except Exception:
            logging.exception('seed 失败，可手动重试')
    # 核算中断恢复：重启后接管所有停留在 processing 的批次
    try:
        with Session() as db:
            ids = recover_stale_batches(db)
        if ids:
            logging.info('启动恢复批次 %s', ids)
    except Exception:
        logging.exception('启动恢复失败，可调用 /imports/recover 手动恢复')
    yield


app = FastAPI(title=CONFIG['title'], lifespan=lifespan)
app.add_middleware(Errors)
app.add_middleware(RateLimit)
for module in (devices, imports, reports, audits):
    app.include_router(module.router)


@app.get('/health')
def health():
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    redis_ok = False
    if REDIS_URL:
        try:
            import redis
            redis.Redis.from_url(REDIS_URL).ping()
            redis_ok = True
        except Exception:
            redis_ok = False
    return {'status': 'healthy', 'redis': redis_ok if REDIS_URL else 'not-configured'}


@app.get('/meta')
def meta():
    return CONFIG
