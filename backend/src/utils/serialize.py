from datetime import datetime


def row(obj):
    out = {}
    for c in obj.__table__.columns:
        value = getattr(obj, c.name)
        if isinstance(value, datetime):
            value = value.isoformat(sep=' ')
        out[c.name] = value
    return out
