from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from app.database import get_db
from app.schemas import UserRegister, UserLogin, Token
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token)
def register(user: UserRegister, db: Session = Depends(get_db)):
    return auth_service.register_user(db, user)


@router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    return auth_service.login_user(db, user)
