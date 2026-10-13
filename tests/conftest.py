import os
import tempfile
import uuid

import pytest
import pytest_asyncio

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-only-32-chars-min")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mktemp(suffix='.db')}")
os.environ.setdefault("MODEL_TYPE", "ollama")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")

from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

TEST_DB_PATH = tempfile.mktemp(suffix=".db")
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(scope="session", autouse=True)
def _create_test_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest_asyncio.fixture
async def client():
    # raise_app_exceptions=False matches real server behavior under uvicorn:
    # an unhandled exception becomes a generic 500 response to the client
    # instead of propagating into the test process.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def registered_user(client):
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "username": f"alice_{suffix}",
        "email": f"alice_{suffix}@example.com",
        "password": "Password123!",
    }
    res = await client.post("/auth/register", json=payload)
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"username": payload["username"], "password": payload["password"], "token": token}
