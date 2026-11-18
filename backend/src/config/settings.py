import os
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / 'project.json').read_text(encoding='utf-8'))

# 本地开发默认 SQLite；docker-compose 通过环境变量切换 MySQL
_DEFAULT_SQLITE_PATH = ROOT / 'data' / 'app.db'
_DEFAULT_SQLITE = f"sqlite:///{_DEFAULT_SQLITE_PATH}"
DATABASE_URL = os.getenv('DATABASE_URL', _DEFAULT_SQLITE)
if DATABASE_URL.startswith('sqlite'):
    _DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
REDIS_URL = os.getenv('REDIS_URL') or None
SECRET = os.getenv('JWT_SECRET', 'meter-reading-local-dev-secret')
HEARTBEAT_FILE = os.getenv('WORKER_HEARTBEAT', '/tmp/worker-heartbeat')
