import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class UserRole(str, enum.Enum):
    USER = "user"
    PRO = "pro"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    username = Column(String(50), primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    token_quota = Column(Integer, default=5000, nullable=False)
    tokens_consumed = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    generations = relationship("GenerationLog", back_populates="user")


class GenerationLog(Base):
    __tablename__ = "generation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), ForeignKey("users.username"), index=True, nullable=False)
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    model_name = Column(String(50), nullable=False)
    provider = Column(String(50), nullable=False)
    tokens_used = Column(Integer, default=0, nullable=False)
    used_fallback = Column(Integer, default=0, nullable=False)  # 0/1 boolean (SQLite-friendly)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="generations")
