from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.database import Base, engine
from app.logging_config import configure_logging
from app.rate_limit import limiter
from app.routers import admin, auth, files, model, oauth


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create any tables that don't exist yet. This project has no
    # migration tool (see MIGRATIONS.md) — schema changes in dev require
    # dropping app.db and letting this recreate it.
    configure_logging()
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: nothing to clean up yet.


app = FastAPI(
    title="RecursiveAI 🧠",
    description="Intelligent text generation powered by open models with JWT authentication",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(model.router)
app.include_router(admin.router)
app.include_router(files.router)
app.include_router(oauth.router)

static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/")
def root():
    return {"message": "Welcome to RecursiveAI 🧠", "app": "Intelligent Text Generation", "demo_url": "/static/demo.html", "docs_url": "/docs"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
