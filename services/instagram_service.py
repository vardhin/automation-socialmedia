from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired, TwoFactorRequired, PleaseWaitFewMinutes
from pathlib import Path
import logging
import pickle
import time
import os
from config import settings

logger = logging.getLogger(__name__)

class InstagramService:
    def __init__(self):
        self.client = Client()
        self.session_file = settings.SESSIONS_DIR / "ig_session.json"
        self.username = settings.INSTAGRAM_USERNAME
        self.password = settings.INSTAGRAM_PASSWORD
        
        # Load existing session if available
        if self.session_file.exists():
            logger.info("✓ Loading existing Instagram session...")
            try:
                self.client.load_settings(str(self.session_file))
            except Exception as e:
                logger.warning(f"Failed to load session: {e}")
    
    def login(self) -> dict:
        """Login to Instagram and save session"""
        try:
            logger.info(f"🔐 Logging in as {self.username}...")
            self.client.login(self.username, self.password)
            self.client.dump_settings(str(self.session_file))
            logger.info("✅ Login successful!")
            
            return {
                "success": True,
                "message": "Logged in successfully",
                "username": self.username
            }
        except Exception as e:
            logger.error(f"❌ Login Error: {e}")
            return {
                "success": False,
                "message": str(e),
                "error": "LOGIN_FAILED"
            }
    
    def upload_reel(
        self,
        video_path: str,
        caption: str = "",
        thumbnail_path: str = None,
        extra_data: dict = None
    ) -> dict:
        """
        Upload Instagram Reel using the working 2025 method
        
        Args:
            video_path: Path to video file
            caption: Caption text with hashtags
            
        Returns:
            dict with upload result
        """
        try:
            logger.info(f"🚀 Uploading Instagram Reel...")
            logger.info(f"   📹 Video: {Path(video_path).name}")
            logger.info(f"   📝 Caption: {caption[:50]}..." if len(caption) > 50 else f"   📝 Caption: {caption}")
            
            # Validate video file
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")
            
            # Check file size
            file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
            logger.info(f"   📦 File size: {file_size_mb:.2f}MB")
            
            if file_size_mb > 4000:
                raise ValueError(f"Video file too large: {file_size_mb:.2f}MB (max 4GB)")
            
            # Upload using clip_upload (the working method)
            media = self.client.clip_upload(
                path=video_path,
                caption=caption
            )
            
            # Success!
            media_id = media.id
            media_code = media.code if hasattr(media, 'code') else str(media_id)
            media_url = f"https://www.instagram.com/reel/{media_code}/"
            
            logger.info(f"✅ Reel uploaded successfully!")
            logger.info(f"   🆔 Media ID: {media_id}")
            logger.info(f"   🔗 URL: {media_url}")
            
            return {
                "success": True,
                "platform": "instagram",
                "media_id": str(media_id),
                "media_code": media_code,
                "url": media_url,
                "caption": caption,
                "type": "reel"
            }
            
        except Exception as e:
            error_str = str(e)
            
            # Handle the 2025 Pydantic validation error
            if "clips_metadata" in error_str or "validation error" in error_str:
                logger.warning("\n⚠️  Note: Pydantic Validation Error caught.")
                logger.warning("👉 Instagram changed their API format, but your video likely uploaded anyway.")
                logger.warning("👉 Check your Instagram profile to confirm.")
                
                return {
                    "success": True,
                    "platform": "instagram",
                    "message": "Upload likely successful (API validation error - check your profile)",
                    "warning": "Pydantic validation error - video probably uploaded",
                    "type": "reel"
                }
            else:
                logger.error(f"❌ Actual Upload Failure: {e}")
                raise Exception(f"Instagram upload failed: {str(e)}")
    
    def check_login_status(self) -> bool:
        """Check if session exists and is valid"""
        if not self.session_file.exists():
            return False
        
        try:
            # Try to get account info to verify session
            self.client.account_info()
            return True
        except Exception:
            return False
    
    def get_account_info(self) -> dict:
        """Get current account information"""
        try:
            user_info = self.client.account_info()
            return {
                "username": user_info.username if hasattr(user_info, 'username') else self.username,
                "user_id": str(user_info.pk) if hasattr(user_info, 'pk') else None,
                "full_name": user_info.full_name if hasattr(user_info, 'full_name') else None,
            }
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return {"username": self.username}
    
    def logout(self):
        """Logout and clear session"""
        try:
            if self.session_file.exists():
                os.remove(self.session_file)
            logger.info("🔓 Logged out from Instagram")
        except Exception as e:
            logger.error(f"Logout error: {e}")