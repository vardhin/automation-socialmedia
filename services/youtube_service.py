from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from pathlib import Path
import asyncio
import random
import logging
from config import settings

logger = logging.getLogger(__name__)

class YouTubeService:
    def __init__(self):
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.playwright = None
        self.user_data_dir = settings.SESSIONS_DIR / "chrome_profile"
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
    
    def session_exists(self) -> bool:
        """Check if session files exist"""
        return (self.user_data_dir / "Default").exists()
    
    async def _init_browser(self, headless: bool = None):
        """Initialize browser with persistent context"""
        if headless is None:
            headless = settings.HEADLESS
        
        if not self.playwright:
            self.playwright = await async_playwright().start()
        
        # Launch with persistent context (saves cookies/session)
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.user_data_dir),
            headless=headless,
            slow_mo=settings.SLOW_MO,
            args=[
                '--disable-blink-features=AutomationControlled',  # Hide automation
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-gpu',
                '--disable-software-rasterizer',
            ],
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
        )
        
        # Set extra headers to appear more human
        await self.context.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
        })
        
        return self.context
    
    async def setup_browser(self) -> str:
        """Open browser for manual login"""
        try:
            await self._init_browser(headless=False)  # Force visible browser
            
            page = await self.context.new_page()
            
            # Navigate to YouTube Studio
            await page.goto('https://studio.youtube.com', wait_until='networkidle')
            
            logger.info("🌐 Browser opened for manual login")
            logger.info("⏳ Waiting for user to login...")
            
            # Wait for user to login (check for YouTube Studio dashboard)
            try:
                await page.wait_for_url('**/studio.youtube.com/**', timeout=300000)  # 5 min
                await asyncio.sleep(2)
                logger.info("✅ Login detected, session saved")
            except:
                logger.warning("⚠️ Timeout waiting for login")
            
            await self.context.close()
            await self.playwright.stop()
            self.context = None
            self.playwright = None
            
            return "https://studio.youtube.com"
            
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            raise
    
    async def check_login_status(self) -> bool:
        """Check if logged in to YouTube"""
        try:
            if not self.session_exists():
                return False
            
            await self._init_browser()
            page = await self.context.new_page()
            
            await page.goto('https://studio.youtube.com', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)
            
            # Check if redirected to login
            is_logged_in = 'accounts.google.com' not in page.url
            
            await page.close()
            await self.context.close()
            await self.playwright.stop()
            self.context = None
            self.playwright = None
            
            return is_logged_in
            
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return False
    
    async def _human_delay(self, min_ms: int = 500, max_ms: int = 2000):
        """Random delay to mimic human behavior"""
        delay = random.uniform(min_ms, max_ms) / 1000
        await asyncio.sleep(delay)
    
    async def _type_like_human(self, element, text: str):
        """Type text with human-like delays"""
        await element.click()
        await self._human_delay(300, 800)
        
        for char in text:
            await element.type(char, delay=random.uniform(50, 150))
    
    async def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        privacy: str,
        tags: list,
        made_for_kids: bool,
        thumbnail_path: str = None
    ):
        """Upload video to YouTube with human-like behavior"""
        try:
            await self._init_browser()
            page = await self.context.new_page()
            
            logger.info("🌐 Navigating to YouTube Studio...")
            await page.goto('https://studio.youtube.com', wait_until='networkidle')
            await self._human_delay(1000, 2000)
            
            # Click CREATE button
            logger.info("🖱️ Clicking CREATE button...")
            create_button = await page.wait_for_selector('button[aria-label="Create"]', timeout=10000)
            await create_button.click()
            await self._human_delay()
            
            # Click "Upload videos"
            upload_button = await page.wait_for_selector('text=Upload videos')
            await upload_button.click()
            await self._human_delay()
            
            # Upload file
            logger.info(f"📤 Uploading file: {video_path}")
            file_input = await page.wait_for_selector('input[type="file"]')
            await file_input.set_input_files(video_path)
            await self._human_delay(3000, 5000)
            
            # Wait for upload to start processing
            await page.wait_for_selector('text=Upload complete', timeout=300000)  # 5 min max
            logger.info("✅ File uploaded, processing...")
            
            # Fill title
            logger.info("✍️ Filling title...")
            title_input = await page.wait_for_selector('#textbox[aria-label*="title"]')
            await title_input.click()
            await title_input.press('Control+A')
            await self._type_like_human(title_input, title)
            await self._human_delay()
            
            # Fill description
            if description:
                logger.info("✍️ Filling description...")
                desc_input = await page.query_selector('#textbox[aria-label*="description"]')
                if desc_input:
                    await self._type_like_human(desc_input, description)
                    await self._human_delay()
            
            # Upload thumbnail (if provided)
            if thumbnail_path:
                logger.info("🖼️ Uploading thumbnail...")
                thumb_input = await page.query_selector('input[type="file"][accept*="image"]')
                if thumb_input:
                    await thumb_input.set_input_files(thumbnail_path)
                    await self._human_delay()
            
            # Handle "Made for kids" setting
            logger.info("👶 Setting audience...")
            if made_for_kids:
                kids_radio = await page.query_selector('#made-for-kids-group tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_MFK"]')
            else:
                kids_radio = await page.query_selector('#made-for-kids-group tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]')
            
            if kids_radio:
                await kids_radio.click()
                await self._human_delay()
            
            # Click NEXT (Details -> Video elements)
            logger.info("⏭️ Proceeding through steps...")
            next_button = await page.wait_for_selector('button:has-text("Next")')
            await next_button.click()
            await self._human_delay(1000, 2000)
            
            # Click NEXT (Video elements -> Checks)
            next_button = await page.wait_for_selector('button:has-text("Next")')
            await next_button.click()
            await self._human_delay(1000, 2000)
            
            # Click NEXT (Checks -> Visibility)
            next_button = await page.wait_for_selector('button:has-text("Next")')
            await next_button.click()
            await self._human_delay(2000, 3000)
            
            # Set privacy
            logger.info(f"🔒 Setting privacy to {privacy}...")
            privacy_map = {
                'private': 'PRIVATE',
                'unlisted': 'UNLISTED',
                'public': 'PUBLIC'
            }
            privacy_radio = await page.query_selector(f'tp-yt-paper-radio-button[name="{privacy_map[privacy]}"]')
            if privacy_radio:
                await privacy_radio.click()
                await self._human_delay()
            
            # Click PUBLISH/SAVE
            logger.info("🚀 Publishing video...")
            publish_button = await page.wait_for_selector('button#done-button')
            await publish_button.click()
            await self._human_delay(3000, 5000)
            
            # Wait for success confirmation
            await page.wait_for_selector('text=Video published', timeout=30000)
            
            # Extract video URL/ID
            video_link = await page.query_selector('a[href*="youtube.com/watch"]')
            video_url = await video_link.get_attribute('href') if video_link else None
            video_id = video_url.split('v=')[1] if video_url else None
            
            logger.info(f"✅ Video published: {video_url}")
            
            await page.close()
            await self.context.close()
            await self.playwright.stop()
            self.context = None
            self.playwright = None
            
            return {
                "success": True,
                "platform": "youtube",
                "video_id": video_id,
                "url": video_url or f"https://studio.youtube.com",
                "title": title,
                "privacy": privacy
            }
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
            self.context = None
            self.playwright = None
            raise Exception(f"YouTube upload failed: {str(e)}")
    
    def clear_session(self):
        """Clear saved session"""
        import shutil
        if self.user_data_dir.exists():
            shutil.rmtree(self.user_data_dir)
            self.user_data_dir.mkdir(parents=True, exist_ok=True)
            logger.info("🗑️ Session cleared")