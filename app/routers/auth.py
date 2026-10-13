from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.rate_limit import limiter
from app.schemas import Token, UserLogin, UserRegister
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token)
@limiter.limit(settings.AUTH_RATE_LIMIT)
def register(request: Request, user: UserRegister, db: Session = Depends(get_db)):
    return auth_service.register_user(db, user)


@router.post("/login", response_model=Token)
@limiter.limit(settings.AUTH_RATE_LIMIT)
def login(request: Request, user: UserLogin, db: Session = Depends(get_db)):
    return auth_service.login_user(db, user)
