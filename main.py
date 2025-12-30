from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from datetime import datetime
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('youtube_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🚀 Starting YouTube Automation Server...")
    logger.info(f"📁 Upload directory: {settings.UPLOAD_DIR}")
    logger.info(f"💾 Sessions directory: {settings.SESSIONS_DIR}")
    logger.info(f"🌐 Headless mode: {settings.HEADLESS}")
    
    yield
    
    logger.info("👋 Server shutdown complete")

app = FastAPI(
    title="YouTube Automation Server",
    description="Stealth YouTube video uploader for Raspberry Pi",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "YouTube Automation Server",
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    import os
    stat = os.statvfs(settings.UPLOAD_DIR)
    free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
    
    return {
        "status": "healthy",
        "disk_space_free": f"{free_gb:.2f} GB",
        "sessions_dir": str(settings.SESSIONS_DIR),
        "timestamp": datetime.now().isoformat()
    }

# Include routers
from routers import storage, youtube

app.include_router(storage.router, prefix="/api/storage", tags=["Storage"])
app.include_router(youtube.router, prefix="/api/youtube", tags=["YouTube"])