from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import logging
from services.instagram_service import InstagramService
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Single service instance
instagram_service = InstagramService()

class InstagramReelUploadRequest(BaseModel):
    video_file_id: str = Field(..., description="The file ID of the uploaded video")
    caption: str = Field("", max_length=2200, description="Caption with hashtags (max 2200 characters)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "video_file_id": "abc123.mp4",
                "caption": "Check out my new reel! 🔥 #reels #instagram #viral"
            }
        }

@router.post("/upload-reel")
async def upload_reel(request: InstagramReelUploadRequest):
    """
    Upload Instagram Reel (auto-login handled automatically)
    
    **Steps:**
    1. Upload video file using `/api/storage/upload-video`
    2. Call this endpoint with the file ID and caption
    
    **Video Requirements:**
    - Format: MP4 (H.264 video, AAC audio recommended)
    - Duration: 3-90 seconds
    - Aspect ratio: 9:16 (vertical) recommended
    - Resolution: 1080x1920 recommended
    - Max size: 4GB
    
    **Note:** Login happens automatically using credentials from .env
    If you see a Pydantic validation error, the video likely uploaded successfully.
    """
    try:
        # Auto-login if needed (handled internally)
        if not instagram_service.check_login_status():
            logger.info("📱 No valid session, logging in...")
            login_result = instagram_service.login()
            if not login_result["success"]:
                raise HTTPException(
                    status_code=401,
                    detail="Failed to login. Check INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in .env"
                )
        
        # Validate video file
        video_path = settings.UPLOAD_DIR / request.video_file_id
        if not video_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Video file not found: {request.video_file_id}"
            )
        
        # Validate video extension
        video_exts = ['.mp4', '.mov']
        if video_path.suffix.lower() not in video_exts:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid video format. Instagram reels require MP4 or MOV format."
            )
        
        # Upload reel
        result = instagram_service.upload_reel(
            video_path=str(video_path),
            caption=request.caption
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Instagram Reel upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))