# app/main.py
# FastAPI application entry point.
# Registers all routers, serves static frontend files, runs DB init on startup.

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.db.connection import init_db
from app.api.routes import upload, generate, caption, music, narration, edit, video, social, status


# ---------------------------------------------------------------------------
# Lifespan: runs init_db() once when server starts
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting PicStory backend...")
    try:
        init_db()
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        print("   Check your .env DB credentials and ensure MySQL is running.")
    yield
    print("👋 Shutting down PicStory backend.")


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="PicStory API",
    description="AI-powered video generation from photos — 22 Indian languages supported.",
    version="2.0.0",
    lifespan=lifespan,
)

# Allow frontend to call API (needed for local dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)


from fastapi.responses import FileResponse
import os

# ---------------------------------------------------------------------------
# Frontend — GET /
# ---------------------------------------------------------------------------
@app.get("/", tags=["Frontend"])
async def serve_frontend():
    index_path = os.path.join(os.getcwd(), "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "ok", "message": "PicStory frontend not found."}


# Global exception handler — show actual error details (dev mode)
from fastapi import Request
from fastapi.responses import JSONResponse
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    print(f"❌ Unhandled error on {request.method} {request.url.path}:\n{tb}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__}
    )


# ---------------------------------------------------------------------------
# Register all route modules
# ---------------------------------------------------------------------------
app.include_router(upload.router,    tags=["Pipeline"])
app.include_router(generate.router,  tags=["Pipeline"])
app.include_router(caption.router,   tags=["Pipeline"])
app.include_router(music.router,     tags=["Pipeline"])
app.include_router(narration.router, tags=["Pipeline"])
app.include_router(edit.router,      tags=["Pipeline"])
app.include_router(video.router,     tags=["Pipeline"])
app.include_router(social.router,    tags=["Pipeline"])
app.include_router(status.router,    tags=["Status"])


# ---------------------------------------------------------------------------
# Serve static frontend files (HTML/CSS/JS)
# ---------------------------------------------------------------------------
import os
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)
os.makedirs("static",  exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
