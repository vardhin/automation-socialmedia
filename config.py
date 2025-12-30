from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # Instagram
    INSTAGRAM_USERNAME: str = ""
    INSTAGRAM_PASSWORD: str = ""
    
    # YouTube
    YOUTUBE_EMAIL: str = ""
    YOUTUBE_PASSWORD: str = ""
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Browser settings
    HEADLESS: bool = True
    SLOW_MO: int = 100
    
    # Paths
    UPLOAD_DIR: Path = Path("./uploads")
    SESSIONS_DIR: Path = Path("./sessions")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # This allows extra fields in .env without errors

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()