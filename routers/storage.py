from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import shutil
import uuid
import logging
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file"""
    try:
        # Validate video file
        allowed_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Generate unique file ID
        file_id = f"{uuid.uuid4()}{file_ext}"
        file_path = settings.UPLOAD_DIR / file_id
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = file_path.stat().st_size
        
        logger.info(f"📹 Video uploaded: {file_id} ({file_size / (1024**2):.2f} MB)")
        
        return {
            "success": True,
            "file_id": file_id,
            "filename": file.filename,
            "size_mb": round(file_size / (1024**2), 2),
            "type": "video"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-thumbnail")
async def upload_thumbnail(file: UploadFile = File(...)):
    """Upload a thumbnail image"""
    try:
        # Validate image file
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif']
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Generate unique file ID
        file_id = f"{uuid.uuid4()}{file_ext}"
        file_path = settings.UPLOAD_DIR / file_id
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = file_path.stat().st_size
        
        # Validate image size (YouTube recommends < 2MB)
        if file_size > 2 * 1024 * 1024:
            logger.warning(f"⚠️ Thumbnail size {file_size / (1024**2):.2f}MB exceeds 2MB recommendation")
        
        logger.info(f"🖼️ Thumbnail uploaded: {file_id} ({file_size / 1024:.2f} KB)")
        
        return {
            "success": True,
            "file_id": file_id,
            "filename": file.filename,
            "size_kb": round(file_size / 1024, 2),
            "type": "thumbnail",
            "warning": "Thumbnail exceeds 2MB" if file_size > 2 * 1024 * 1024 else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Thumbnail upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_files():
    """List all uploaded files"""
    try:
        files = []
        
        for file_path in settings.UPLOAD_DIR.glob("*"):
            if file_path.is_file():
                stat = file_path.stat()
                file_ext = file_path.suffix.lower()
                
                # Determine file type
                video_exts = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
                image_exts = ['.jpg', '.jpeg', '.png', '.gif']
                
                if file_ext in video_exts:
                    file_type = "video"
                elif file_ext in image_exts:
                    file_type = "thumbnail"
                else:
                    file_type = "unknown"
                
                files.append({
                    "file_id": file_path.name,
                    "size_mb": round(stat.st_size / (1024**2), 2),
                    "created": stat.st_ctime,
                    "type": file_type
                })
        
        return {
            "files": files,
            "total": len(files)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete/{file_id}")
async def delete_file(file_id: str):
    """Delete a file"""
    try:
        file_path = settings.UPLOAD_DIR / file_id
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path.unlink()
        logger.info(f"🗑️ Deleted: {file_id}")
        
        return {"success": True, "message": f"Deleted {file_id}"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/info/{file_id}")
async def get_file_info(file_id: str):
    """Get file information"""
    try:
        file_path = settings.UPLOAD_DIR / file_id
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        stat = file_path.stat()
        file_ext = file_path.suffix.lower()
        
        video_exts = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
        image_exts = ['.jpg', '.jpeg', '.png', '.gif']
        
        if file_ext in video_exts:
            file_type = "video"
        elif file_ext in image_exts:
            file_type = "thumbnail"
        else:
            file_type = "unknown"
        
        return {
            "file_id": file_id,
            "size_mb": round(stat.st_size / (1024**2), 2),
            "created": stat.st_ctime,
            "type": file_type,
            "extension": file_ext
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))