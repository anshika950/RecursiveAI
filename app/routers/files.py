import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_object
from app.models import Document, User
from app.services.vector_store import add_document_chunks, chunk_text, list_documents

router = APIRouter(prefix="/files", tags=["files"])

ALLOWED_EXTENSIONS = {".txt", ".md", ".json", ".csv"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_object),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB limit.",
        )
    if len(file_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty.")

    text_content = file_bytes.decode("utf-8", errors="replace")

    document = Document(
        filename=file.filename,
        owner_username=current_user.username,
        content_text=text_content,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    chunks = chunk_text(text_content)
    chunk_count = add_document_chunks(db, document.id, current_user.username, chunks)

    return {
        "document_id": document.id,
        "filename": document.filename,
        "size_kb": round(len(file_bytes) / 1024, 2),
        "chunk_count": chunk_count,
    }


@router.get("/")
def list_my_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_object),
):
    documents = list_documents(db, current_user.username)
    return [
        {"document_id": d.id, "filename": d.filename, "created_at": d.created_at}
        for d in documents
    ]
