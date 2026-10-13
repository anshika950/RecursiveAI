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
    documents = relationship("Document", back_populates="owner")


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


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    owner_username = Column(String(50), ForeignKey("users.username"), index=True, nullable=False)
    content_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), index=True, nullable=False)
    owner_username = Column(String(50), ForeignKey("users.username"), index=True, nullable=False)
    chunk_text = Column(Text, nullable=False)
    # No persisted vector column: TF-IDF vector dimensionality depends on
    # the fitted vocabulary, so a vector saved from one fit isn't
    # comparable to a vector from a later fit (e.g. after a new document
    # changes the vocabulary). VectorStore.search() refits the vectorizer
    # over this owner's current chunks + the query at search time instead
    # of trusting a stored-but-potentially-stale vector.

    document = relationship("Document", back_populates="chunks")
