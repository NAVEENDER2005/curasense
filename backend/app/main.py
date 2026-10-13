import os
import pathlib
import sys
from contextlib import asynccontextmanager

# Ensure the repo root (parent of backend/ and ai/) is importable regardless
# of how uvicorn was launched, so `from ai...` imports always resolve.
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.db import create_pool  # noqa: E402
from app.routers import appeals, chat, claims, dashboard, policies  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await create_pool()
    yield
    await app.state.pool.close()


app = FastAPI(title="CuraSense AI", version="0.1.0", lifespan=lifespan)

cors_origins_raw = os.environ.get("CORS_ORIGINS", "*")
cors_origins = [o.strip() for o in cors_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if "*" not in cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(claims.router)
app.include_router(dashboard.router)
app.include_router(appeals.router)
app.include_router(policies.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    return {
        "name": "CuraSense AI API",
        "status": "online",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
