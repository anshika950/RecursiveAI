from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import auth, model


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create any tables that don't exist yet. This project has no
    # migration tool (see MIGRATIONS.md) — schema changes in dev require
    # dropping app.db and letting this recreate it.
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: nothing to clean up yet.


app = FastAPI(
    title="RecursiveAI 🧠",
    description="Intelligent text generation powered by open models with JWT authentication",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(model.router)

static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/")
def root():
    return {"message": "Welcome to RecursiveAI 🧠", "app": "Intelligent Text Generation", "demo_url": "/static/demo.html", "docs_url": "/docs"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
