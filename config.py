from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Storage paths
    UPLOAD_DIR: Path = Path.home() / "social_media_uploads"
    SESSIONS_DIR: Path = Path.home() / ".youtube_automation"
    
    # Browser settings
    HEADLESS: bool = True
    SLOW_MO: int = 100  # Milliseconds delay between actions
    
    # YouTube
    YOUTUBE_EMAIL: str = ""
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    class Config:
        env_file = ".env"

settings = Settings()

# Create directories
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)