"""A small, from-scratch vector-search layer for retrieval-augmented
generation (RAG), built on TF-IDF (scikit-learn) + cosine similarity
instead of neural embeddings (sentence-transformers) and a dedicated
vector database (Chroma/FAISS).

Why: neural embedding models are normally pulled from the Hugging Face
Hub at first use, and this project's deployment environment cannot
resolve huggingface.co. TF-IDF needs no pretrained weights at all --
it's a classic, fully-offline information-retrieval technique -- so it
installs and runs anywhere `scikit-learn` does. It's a real, working
vector-search implementation, just not a neural one.

Vectors are intentionally not persisted (see the comment on
DocumentChunk in app/models.py): TF-IDF vector dimensionality depends on
the fitted vocabulary, so a vector from one fit isn't comparable to a
vector from a later fit over a different corpus. search() always refits
over the current corpus + the query, which is cheap at the scale a
single user's uploaded documents reach here.
"""

from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Fixed-size overlapping chunks. No NLP tokenizer needed for this --
    it's just a sliding window over characters."""
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    step = max(chunk_size - overlap, 1)
    while start < len(text):
        chunk = text[start : start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks


def add_document_chunks(db: Session, document_id: int, owner_username: str, chunks: list[str]) -> int:
    """Persists chunk text rows for a document. Returns the number of
    chunks stored."""
    for chunk in chunks:
        db.add(
            DocumentChunk(
                document_id=document_id,
                owner_username=owner_username,
                chunk_text=chunk,
            )
        )
    db.commit()
    return len(chunks)


def search(db: Session, query: str, owner_username: str, top_k: int = 3) -> list[str]:
    """Returns up to top_k chunk texts belonging to owner_username, ranked
    by TF-IDF cosine similarity to the query. Returns [] if the owner has
    no chunks at all."""
    rows = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.owner_username == owner_username)
        .all()
    )
    if not rows:
        return []

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    corpus_texts = [row.chunk_text for row in rows]
    vectorizer = TfidfVectorizer(stop_words="english")
    # Fit over the corpus + the query together so both end up in the same
    # vector space, then split the result back apart.
    all_vectors = vectorizer.fit_transform(corpus_texts + [query])
    corpus_vectors, query_vector = all_vectors[:-1], all_vectors[-1]

    similarities = cosine_similarity(query_vector, corpus_vectors)[0]
    ranked_indices = similarities.argsort()[::-1][:top_k]
    return [corpus_texts[i] for i in ranked_indices if similarities[i] > 0]


def list_documents(db: Session, owner_username: str) -> list[Document]:
    return db.query(Document).filter(Document.owner_username == owner_username).all()
