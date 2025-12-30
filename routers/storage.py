from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import aiofiles
import uuid
import logging
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload video file to server"""
    try:
        # Validate file type
        allowed_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Allowed: {allowed_extensions}"
            )
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = settings.UPLOAD_DIR / unique_filename
        
        # Save file in chunks (memory efficient for Pi)
        async with aiofiles.open(file_path, 'wb') as f:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                await f.write(chunk)
        
        size_mb = file_path.stat().st_size / (1024**2)
        logger.info(f"✅ Video uploaded: {unique_filename} ({size_mb:.2f} MB)")
        
        return {
            "success": True,
            "file_id": unique_filename,
            "file_path": str(file_path),
            "size_mb": round(size_mb, 2),
            "original_name": file.filename
        }
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files")
async def list_files():
    """List all uploaded files"""
    files = []
    for file_path in settings.UPLOAD_DIR.iterdir():
        if file_path.is_file():
            stat = file_path.stat()
            files.append({
                "file_id": file_path.name,
                "size_mb": round(stat.st_size / (1024**2), 2),
                "created": stat.st_ctime
            })
    return {"files": files, "count": len(files)}

@router.delete("/file/{file_id}")
async def delete_file(file_id: str):
    """Delete uploaded file"""
    file_path = settings.UPLOAD_DIR / file_id
    if file_path.exists():
        file_path.unlink()
        logger.info(f"🗑️ File deleted: {file_id}")
        return {"success": True, "message": "File deleted"}
    raise HTTPException(status_code=404, detail="File not found")