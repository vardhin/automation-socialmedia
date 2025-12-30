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

def print_api_usage():
    """Print API usage examples"""
    print("\n" + "="*80)
    print("📚 API USAGE EXAMPLES")
    print("="*80)
    
    print("\n🔹 STORAGE ENDPOINTS")
    print("-" * 80)
    print("Upload video:")
    print('  curl -X POST "http://localhost:8000/api/storage/upload-video" \\')
    print('    -F "file=@/path/to/video.mp4"')
    
    print("\nUpload thumbnail:")
    print('  curl -X POST "http://localhost:8000/api/storage/upload-thumbnail" \\')
    print('    -F "file=@/path/to/thumbnail.jpg"')
    
    print("\nList files:")
    print('  curl "http://localhost:8000/api/storage/list"')
    
    print("\nGet file info:")
    print('  curl "http://localhost:8000/api/storage/info/{file_id}"')
    
    print("\nDelete file:")
    print('  curl -X DELETE "http://localhost:8000/api/storage/delete/{file_id}"')
    
    print("\n🔹 INSTAGRAM REEL UPLOAD (Auto-Login)")
    print("-" * 80)
    print("Upload Instagram Reel (credentials from .env):")
    print('  curl -X POST "http://localhost:8000/api/instagram/upload-reel" \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"video_file_id": "your-file-id.mp4", "caption": "Check this out! 🔥 #viral"}\'')
    
    print("\n💡 Note: Login happens automatically, no need for separate login endpoint!")
    
    print("\n🔹 YOUTUBE ENDPOINTS")
    print("-" * 80)
    print("Setup browser for manual login (first time only):")
    print('  curl -X POST "http://localhost:8000/api/youtube/setup-browser"')
    
    print("\nCheck YouTube login status:")
    print('  curl "http://localhost:8000/api/youtube/status"')
    
    print("\nUpload YouTube video:")
    print('  curl -X POST "http://localhost:8000/api/youtube/upload" \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"video_file_id": "your-file-id.mp4", "title": "My Video", \\')
    print('         "description": "Video description", "privacy": "private", \\')
    print('         "made_for_kids": false, "tags": ["gaming", "tutorial"]}\'')
    
    print("\nClear YouTube session:")
    print('  curl -X DELETE "http://localhost:8000/api/youtube/clear-session"')
    
    print("\n🔹 HEALTH CHECK")
    print("-" * 80)
    print("Check server health:")
    print('  curl "http://localhost:8000/health"')
    
    print("\n🔹 COMPLETE WORKFLOW EXAMPLE")
    print("-" * 80)
    print("1. Upload video:")
    print('   VIDEO_ID=$(curl -s -X POST "http://localhost:8000/api/storage/upload-video" \\')
    print('     -F "file=@video.mp4" | jq -r \'.file_id\')')
    
    print("\n2. Upload to Instagram (auto-login):")
    print('   curl -X POST "http://localhost:8000/api/instagram/upload-reel" \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -d "{\"video_file_id\": \"$VIDEO_ID\", \"caption\": \"Amazing! 🚀 #viral\"}"')
    
    print("\n3. Upload to YouTube:")
    print('   curl -X POST "http://localhost:8000/api/youtube/upload" \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -d "{\"video_file_id\": \"$VIDEO_ID\", \"title\": \"My Video\", \\')
    print('          \"privacy\": \"unlisted\", \"made_for_kids\": false}"')
    
    print("\n🔹 INTERACTIVE DOCS")
    print("-" * 80)
    print("Swagger UI:  http://localhost:8000/docs")
    print("ReDoc:       http://localhost:8000/redoc")
    
    print("\n" + "="*80 + "\n")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🚀 Starting Social Media Automation Server...")
    logger.info(f"📁 Upload directory: {settings.UPLOAD_DIR}")
    logger.info(f"💾 Sessions directory: {settings.SESSIONS_DIR}")
    logger.info(f"🌐 Headless mode: {settings.HEADLESS}")
    logger.info(f"📱 Instagram: {settings.INSTAGRAM_USERNAME}")
    logger.info(f"📺 YouTube: {settings.YOUTUBE_EMAIL}")
    
    # Print API usage examples
    print_api_usage()
    
    yield
    
    logger.info("👋 Server shutdown complete")

app = FastAPI(
    title="Social Media Automation Server",
    description="Upload videos to YouTube and Instagram automatically",
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
        "message": "Social Media Automation Server",
        "status": "healthy",
        "version": "1.0.0",
        "platforms": ["instagram", "youtube"],
        "docs": "/docs",
        "redoc": "/redoc"
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
        "instagram_configured": bool(settings.INSTAGRAM_USERNAME),
        "youtube_configured": bool(settings.YOUTUBE_EMAIL),
        "timestamp": datetime.now().isoformat()
    }

# Include routers
from routers import storage, youtube, instagram

app.include_router(storage.router, prefix="/api/storage", tags=["Storage"])
app.include_router(youtube.router, prefix="/api/youtube", tags=["YouTube"])
app.include_router(instagram.router, prefix="/api/instagram", tags=["Instagram"])