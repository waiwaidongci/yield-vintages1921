from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from src.config.settings import DATABASE_URL

_connect_args = {'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=_connect_args)

if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def _sqlite_pragma(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute('PRAGMA foreign_keys=ON')
        cur.close()


class Base(DeclarativeBase):
    pass


Session = sessionmaker(bind=engine, expire_on_commit=False)


def database():
    with Session() as db:
        yield db
