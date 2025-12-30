from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Literal
import logging
from services.youtube_service import YouTubeService
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

youtube_service = YouTubeService()

class YouTubeUploadRequest(BaseModel):
    video_file_id: str = Field(..., description="The file ID of the uploaded video")
    title: str = Field(..., min_length=1, max_length=100, description="Video title (max 100 characters)")
    description: Optional[str] = Field("", max_length=5000, description="Video description (max 5000 characters)")
    thumbnail_file_id: Optional[str] = Field(None, description="The file ID of the uploaded thumbnail image (optional)")
    privacy: Literal["private", "unlisted", "public"] = Field("private", description="Video privacy setting")
    made_for_kids: bool = Field(False, description="Is this video made for kids?")
    tags: Optional[list[str]] = Field([], description="Video tags (optional)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "video_file_id": "57e097ce-e5a4-4745-b3eb-a089f6dce316.mp4",
                "title": "My Awesome Video",
                "description": "This is a description of my video",
                "thumbnail_file_id": "abc123-thumbnail.jpg",
                "privacy": "private",
                "made_for_kids": False,
                "tags": ["gaming", "tutorial", "fun"]
            }
        }

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
    """
    Upload video to YouTube
    
    **Steps:**
    1. Upload video file using `/api/storage/upload-video`
    2. (Optional) Upload thumbnail using `/api/storage/upload-thumbnail`
    3. Call this endpoint with the file IDs and metadata
    """
    try:
        # Validate video file exists
        video_path = settings.UPLOAD_DIR / request.video_file_id
        if not video_path.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"Video file not found: {request.video_file_id}"
            )
        
        # Validate video is actually a video file
        video_exts = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
        if video_path.suffix.lower() not in video_exts:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid video file type. Must be one of: {', '.join(video_exts)}"
            )
        
        # Validate thumbnail if provided
        thumbnail_path = None
        if request.thumbnail_file_id:
            thumbnail_path = settings.UPLOAD_DIR / request.thumbnail_file_id
            if not thumbnail_path.exists():
                raise HTTPException(
                    status_code=404, 
                    detail=f"Thumbnail file not found: {request.thumbnail_file_id}"
                )
            
            # Validate thumbnail is an image
            image_exts = ['.jpg', '.jpeg', '.png', '.gif']
            if thumbnail_path.suffix.lower() not in image_exts:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid thumbnail file type. Must be one of: {', '.join(image_exts)}"
                )
        
        # Check if logged in
        if not await youtube_service.check_login_status():
            raise HTTPException(
                status_code=401, 
                detail="Not logged in to YouTube. Please run /api/youtube/setup-browser first"
            )
        
        logger.info(f"📤 Starting YouTube upload: {request.title}")
        logger.info(f"   📹 Video: {request.video_file_id}")
        if request.thumbnail_file_id:
            logger.info(f"   🖼️ Thumbnail: {request.thumbnail_file_id}")
        logger.info(f"   🔒 Privacy: {request.privacy}")
        
        # Upload video (this will take time)
        result = await youtube_service.upload_video(
            video_path=str(video_path),
            title=request.title,
            description=request.description,
            privacy=request.privacy,
            tags=request.tags,
            made_for_kids=request.made_for_kids,
            thumbnail_path=str(thumbnail_path) if thumbnail_path else None
        )
        
        logger.info(f"✅ YouTube upload complete!")
        logger.info(f"   🆔 Video ID: {result.get('video_id')}")
        logger.info(f"   🔗 URL: {result.get('url')}")
        
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