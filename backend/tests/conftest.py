import os
import sys
import tempfile
from pathlib import Path

import pytest

# 隔离每个测试会话的 SQLite 数据库
_tmp_db = Path(tempfile.mkdtemp(prefix='meter-test-')) / 'test.db'
os.environ['DATABASE_URL'] = f'sqlite:///{_tmp_db}'
os.environ.setdefault('JWT_SECRET', 'test-secret')
os.environ.pop('REDIS_URL', None)  # 队列走内存降级

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from src.config.database import Base, engine, Session  # noqa: E402
from src.main import app  # noqa: E402
from src.models.entities import Device  # noqa: E402
from src.constants.enums import DEFAULT_SHIFTS  # noqa: E402


@pytest.fixture(scope='session', autouse=True)
def _schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _clean_tables():
    """每个用例独立数据，避免唯一约束跨用例冲突。"""
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    yield


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db():
    # 每个用例独立 Session，避免与服务内部保存点事务共享状态
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def device(db):
    obj = Device(code='T-01', name='测试机', counter_capacity=10000,
                 max_rate_per_sec=2, shifts=DEFAULT_SHIFTS)
    db.add(obj)
    db.commit()  # 独立连接提交，保证服务侧独立事务可见
    db.refresh(obj)
    return obj
