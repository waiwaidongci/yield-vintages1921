from src.models.entities import AuditLog


def log(db, actor: str, action: str, target: str | None = None, detail: str | None = None):
    db.add(AuditLog(actor=actor[:120], action=action, target=target, detail=detail))
