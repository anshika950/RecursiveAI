from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import GenerationLog, User, UserRole

router = APIRouter(prefix="/admin", tags=["admin"])

_admin_only = require_role([UserRole.ADMIN])


@router.get("/users")
def list_users(db: Session = Depends(get_db), _admin: User = Depends(_admin_only)):
    users = db.query(User).all()
    return [
        {
            "username": u.username,
            "email": u.email,
            "role": u.role.value if u.role else UserRole.USER.value,
            "token_quota": u.token_quota,
            "tokens_consumed": u.tokens_consumed,
        }
        for u in users
    ]


@router.get("/stats")
def generation_stats(db: Session = Depends(get_db), _admin: User = Depends(_admin_only)):
    total_requests = db.query(func.count(GenerationLog.id)).scalar() or 0
    total_tokens = db.query(func.sum(GenerationLog.tokens_used)).scalar() or 0
    fallback_count = (
        db.query(func.count(GenerationLog.id)).filter(GenerationLog.used_fallback == 1).scalar() or 0
    )
    return {
        "total_requests": total_requests,
        "total_tokens_used": int(total_tokens),
        "fallback_responses": fallback_count,
    }
