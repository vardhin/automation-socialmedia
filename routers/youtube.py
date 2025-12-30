from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Literal
import logging
from services.youtube_service import YouTubeService
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

youtube_service = YouTubeService()

class YouTubeUploadRequest(BaseModel):
    file_id: str
    title: str
    description: Optional[str] = ""
    privacy: Literal["private", "unlisted", "public"] = "private"
    category: Optional[str] = "22"  # People & Blogs
    tags: Optional[list[str]] = []
    playlist: Optional[str] = None  # Playlist name (optional)
    made_for_kids: bool = False
    thumbnail_file_id: Optional[str] = None

@router.post("/setup-browser")
async def setup_browser():
    """Initialize browser for manual login (one-time setup)"""
    try:
        url = await youtube_service.setup_browser()
        return {
            "success": True,
            "message": "Browser opened. Please login manually.",
            "url": url,
            "instructions": [
                "1. Login to your Google account",
                "2. Navigate to YouTube Studio",
                "3. Once logged in, close the browser",
                "4. Session will be saved automatically"
            ]
        }
    except Exception as e:
        logger.error(f"❌ Browser setup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def check_status():
    """Check if YouTube session is valid"""
    try:
        is_logged_in = await youtube_service.check_login_status()
        return {
            "logged_in": is_logged_in,
            "session_exists": youtube_service.session_exists(),
            "email": settings.YOUTUBE_EMAIL if is_logged_in else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_video(request: YouTubeUploadRequest, background_tasks: BackgroundTasks):
    """Upload video to YouTube"""
    try:
        # Validate file exists
        file_path = settings.UPLOAD_DIR / request.file_id
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Video file not found")
        
        # Validate thumbnail if provided
        thumbnail_path = None
        if request.thumbnail_file_id:
            thumbnail_path = settings.UPLOAD_DIR / request.thumbnail_file_id
            if not thumbnail_path.exists():
                raise HTTPException(status_code=404, detail="Thumbnail file not found")
        
        # Check if logged in
        if not await youtube_service.check_login_status():
            raise HTTPException(
                status_code=401, 
                detail="Not logged in. Please run /setup-browser first"
            )
        
        logger.info(f"📤 Starting YouTube upload: {request.title}")
        
        # Upload video (this will take time)
        result = await youtube_service.upload_video(
            video_path=str(file_path),
            title=request.title,
            description=request.description,
            privacy=request.privacy,
            tags=request.tags,
            made_for_kids=request.made_for_kids,
            thumbnail_path=str(thumbnail_path) if thumbnail_path else None
        )
        
        logger.info(f"✅ YouTube upload complete: {result.get('video_id')}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ YouTube upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clear-session")
async def clear_session():
    """Clear saved YouTube session (logout)"""
    try:
        youtube_service.clear_session()
        return {"success": True, "message": "Session cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))