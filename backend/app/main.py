"""Update main.py to include the AI orchestrator router."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, assets, ai_orchestrator
from app.api.v1.signaling import router as signaling_router
from app.config import settings
from app.database import init_db

app = FastAPI(title=settings.app_name, version="0.1.0", debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    await init_db()


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.app_name}


app.include_router(auth.router, prefix="/api/v1")
app.include_router(assets.router, prefix="/api/v1")
app.include_router(ai_orchestrator.router, prefix="/api/v1")
app.include_router(signaling_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "LivePortrait-WebRTC API", "version": "0.1.0"}
