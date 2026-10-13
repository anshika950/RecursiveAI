from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import verify_token
from app.database import get_db
from app.models import User


def get_current_user_object(
    username: str = Depends(verify_token),
    db: Session = Depends(get_db),
) -> User:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
