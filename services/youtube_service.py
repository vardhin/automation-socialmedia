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
                '--disable-blink-features=AutomationControlled',
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
        
        await self.context.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
        })
        
        return self.context
    
    async def _check_and_handle_verify_dialog(self, page: Page) -> bool:
        """Check for and handle 'Verify it's you' dialog"""
        try:
            # Look for the verification dialog
            verify_dialog = await page.query_selector('text=Verify it\'s you')
            
            if verify_dialog:
                logger.warning("⚠️ 'Verify it's you' dialog detected!")
                logger.warning("⚠️ This requires manual intervention - Google wants to verify your identity")
                
                # Take screenshot for user to see
                await page.screenshot(path='/tmp/youtube_verify_dialog.png')
                logger.info("📸 Verification dialog screenshot: /tmp/youtube_verify_dialog.png")
                
                # Check if there's a "Next" button
                next_button = await page.query_selector('button:has-text("Next")')
                if next_button:
                    logger.info("🔘 Found 'Next' button, clicking...")
                    await next_button.click()
                    await asyncio.sleep(3)
                    
                    # Wait for dialog to disappear or for user action
                    logger.warning("⏳ Please complete the verification in the browser window...")
                    logger.warning("⏳ Waiting up to 5 minutes for verification...")
                    
                    for i in range(300):  # Wait up to 5 minutes
                        verify_still_there = await page.query_selector('text=Verify it\'s you')
                        if not verify_still_there:
                            logger.info("✅ Verification dialog closed!")
                            return True
                        
                        if i % 30 == 0:
                            logger.info(f"⏳ Still waiting for verification... ({i}s/300s)")
                        
                        await asyncio.sleep(1)
                    
                    logger.error("❌ Verification timeout - dialog still present after 5 minutes")
                    return False
                else:
                    logger.error("❌ Verification dialog present but no 'Next' button found")
                    logger.error("❌ This requires MANUAL verification - please complete it in the browser")
                    return False
            
            return True  # No dialog, all good
            
        except Exception as e:
            logger.error(f"Error checking verify dialog: {e}")
            return True  # Don't block on error
    
    async def setup_browser(self) -> str:
        """Open browser for manual login"""
        try:
            await self._init_browser(headless=False)
            
            page = await self.context.new_page()
            
            await page.goto('https://studio.youtube.com', wait_until='networkidle')
            
            logger.info("🌐 Browser opened for manual login")
            logger.info("⏳ Waiting for user to login...")
            
            try:
                await page.wait_for_url('**/studio.youtube.com/**', timeout=300000)
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
        """Upload video to YouTube with exact selectors"""
        page = None
        try:
            await self._init_browser()
            page = await self.context.new_page()
            
            logger.info("🌐 Navigating to YouTube Studio...")
            await page.goto('https://studio.youtube.com', wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)
            
            # Check for verification dialog immediately
            if not await self._check_and_handle_verify_dialog(page):
                raise Exception("Verification dialog requires manual intervention. Please complete verification and try again.")
            
            # Take screenshot for debugging
            await page.screenshot(path='/tmp/youtube_studio.png')
            logger.info("📸 Screenshot saved: /tmp/youtube_studio.png")
            
            # Click the circular "Upload videos" button (top right)
            logger.info("🖱️ Clicking Upload videos button...")
            try:
                upload_icon = await page.wait_for_selector('ytcp-icon-button#upload-icon', timeout=10000)
                await upload_icon.click()
                logger.info("✅ Clicked Upload videos button")
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"❌ Could not find upload icon: {e}")
                await page.screenshot(path='/tmp/youtube_no_upload_button.png')
                raise Exception("Could not find upload button")
            
            # Check for verification dialog after clicking upload
            if not await self._check_and_handle_verify_dialog(page):
                raise Exception("Verification dialog appeared after clicking upload. Please complete verification and try again.")
            
            # Take screenshot of modal
            await page.screenshot(path='/tmp/youtube_modal_opened.png')
            logger.info("📸 Modal screenshot saved")
            
            # Find and click "Select files" button in modal
            logger.info("📤 Looking for file input...")
            try:
                # The file input is hidden, so we need to find it and set files directly
                file_input = await page.wait_for_selector('input[type="file"]', timeout=10000, state='attached')
                logger.info(f"✅ Found file input, uploading: {video_path}")
                await file_input.set_input_files(video_path)
                logger.info("✅ File selected successfully")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"❌ Could not find file input: {e}")
                await page.screenshot(path='/tmp/youtube_no_file_input.png')
                raise Exception("Could not find file input in modal")
            
            # Wait for upload to complete and details page to load
            logger.info("⏳ Waiting for upload to complete...")
            try:
                # Wait for title textbox to appear (indicates upload is done and we're on details page)
                await page.wait_for_selector('div#textbox[contenteditable="true"][aria-label*="title"]', timeout=300000)
                logger.info("✅ Upload complete, details page loaded")
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"❌ Timeout waiting for upload: {e}")
                await page.screenshot(path='/tmp/youtube_upload_timeout.png')
                raise Exception("Upload timeout or details page not loaded")
            
            # Check for verification dialog again
            if not await self._check_and_handle_verify_dialog(page):
                raise Exception("Verification dialog appeared during upload. Please complete verification and try again.")
            
            # Fill title
            logger.info("✍️ Filling title...")
            try:
                title_box = await page.wait_for_selector('div#textbox[contenteditable="true"][aria-label*="title"]', timeout=10000)
                await title_box.click()
                await asyncio.sleep(0.3)
                # Clear existing text
                await page.keyboard.press('Control+A')
                await asyncio.sleep(0.2)
                # Type new title
                await title_box.type(title, delay=50)
                logger.info(f"✅ Title filled: {title}")
                await asyncio.sleep(1)
            except Exception as e:
                logger.warning(f"⚠️ Could not fill title: {e}")
                await page.screenshot(path='/tmp/youtube_title_error.png')
            
            # Fill description
            if description:
                logger.info("✍️ Filling description...")
                try:
                    desc_box = await page.wait_for_selector('div#textbox[contenteditable="true"][aria-label*="Tell viewers"]', timeout=5000)
                    await desc_box.click()
                    await asyncio.sleep(0.3)
                    await desc_box.type(description, delay=50)
                    logger.info(f"✅ Description filled")
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.warning(f"⚠️ Could not fill description: {e}")
            
            # Upload thumbnail (if provided)
            if thumbnail_path:
                logger.info("🖼️ Uploading thumbnail...")
                try:
                    # Find the hidden file input and upload directly
                    thumb_input = await page.query_selector('input[type="file"][accept*="image"]')
                    if thumb_input:
                        await thumb_input.set_input_files(thumbnail_path)
                        logger.info("✅ Thumbnail uploaded")
                        await asyncio.sleep(2)
                    else:
                        logger.warning("⚠️ Could not find thumbnail input")
                except Exception as e:
                    logger.warning(f"⚠️ Could not upload thumbnail: {e}")
            
            # Scroll down to see "Made for kids" section
            await page.evaluate('window.scrollBy(0, 400)')
            await asyncio.sleep(1)
            
            # Set "Made for kids" option
            logger.info("👶 Setting audience (Made for kids)...")
            try:
                if made_for_kids:
                    # Click "Yes, it's made for kids"
                    kids_yes = await page.wait_for_selector('tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_MFK"]', timeout=5000)
                    await kids_yes.click()
                    logger.info("✅ Set as 'Made for kids'")
                else:
                    # Click "No, it's not made for kids"
                    kids_no = await page.wait_for_selector('tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]', timeout=5000)
                    await kids_no.click()
                    logger.info("✅ Set as 'Not made for kids'")
                await asyncio.sleep(1)
            except Exception as e:
                logger.warning(f"⚠️ Could not set audience: {e}")
                await page.screenshot(path='/tmp/youtube_audience_error.png')
            
            # Click NEXT button (Details -> Video elements)
            logger.info("⏭️ Step 1: Details -> Video elements")
            try:
                next_button = await page.wait_for_selector('ytcp-button#next-button', timeout=10000)
                await next_button.click()
                logger.info("✅ Clicked Next (Step 1)")
                await asyncio.sleep(2)
            except Exception as e:
                logger.warning(f"⚠️ Step 1 Next button failed: {e}")
                await page.screenshot(path='/tmp/youtube_step1_error.png')
            
            # Click NEXT button (Video elements -> Checks)
            logger.info("⏭️ Step 2: Video elements -> Checks")
            try:
                next_button = await page.wait_for_selector('ytcp-button#next-button', timeout=10000)
                await next_button.click()
                logger.info("✅ Clicked Next (Step 2)")
                await asyncio.sleep(2)
            except Exception as e:
                logger.warning(f"⚠️ Step 2 Next button failed: {e}")
                await page.screenshot(path='/tmp/youtube_step2_error.png')
            
            # Wait for checks to complete, then click NEXT (Checks -> Visibility)
            logger.info("⏭️ Step 3: Checks -> Visibility (waiting for processing)")
            try:
                logger.info("⏳ Waiting for SD processing to complete (up to 10 minutes)...")
                
                # Wait for Next button to become enabled
                max_wait = 600  # 10 minutes
                for i in range(max_wait):
                    try:
                        # Check if button exists and is not disabled
                        next_button = await page.query_selector('ytcp-button#next-button:not([disabled])')
                        if next_button:
                            is_enabled = await next_button.is_enabled()
                            if is_enabled:
                                logger.info("✅ Checks complete!")
                                break
                    except:
                        pass
                    
                    if i % 10 == 0:
                        logger.info(f"⏳ Still waiting... ({i}s/{max_wait}s)")
                    
                    await asyncio.sleep(1)
                
                # Click Next
                next_button = await page.wait_for_selector('ytcp-button#next-button', timeout=10000)
                await next_button.click()
                logger.info("✅ Clicked Next (Step 3)")
                await asyncio.sleep(3)
            except Exception as e:
                logger.warning(f"⚠️ Step 3 Next button failed: {e}")
                await page.screenshot(path='/tmp/youtube_step3_error.png')
            
            # Set privacy to public/private/unlisted
            logger.info(f"🔒 Setting privacy to: {privacy}")
            try:
                privacy_map = {
                    'private': 'PRIVATE',
                    'unlisted': 'UNLISTED',
                    'public': 'PUBLIC'
                }
                
                privacy_selector = f'tp-yt-paper-radio-button[name="{privacy_map[privacy]}"]'
                privacy_button = await page.wait_for_selector(privacy_selector, timeout=10000)
                await privacy_button.click()
                logger.info(f"✅ Privacy set to: {privacy}")
                await asyncio.sleep(2)
            except Exception as e:
                logger.warning(f"⚠️ Could not set privacy: {e}")
                await page.screenshot(path='/tmp/youtube_privacy_error.png')
            
            # Click PUBLISH button
            logger.info("🚀 Publishing video...")
            try:
                publish_button = await page.wait_for_selector('ytcp-button#done-button', timeout=10000)
                await publish_button.click()
                logger.info("✅ Clicked Publish button")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"❌ Could not click publish button: {e}")
                await page.screenshot(path='/tmp/youtube_publish_error.png')
                raise Exception("Could not publish video")
            
            # Extract video URL from the share dialog
            logger.info("🔗 Extracting video URL...")
            video_url = None
            video_id = None
            try:
                # Wait for the share URL to appear
                url_link = await page.wait_for_selector('a#share-url', timeout=30000)
                video_url = await url_link.get_attribute('href')
                
                if video_url:
                    # Extract video ID from URL (youtu.be/VIDEO_ID or youtube.com/watch?v=VIDEO_ID)
                    if 'youtu.be/' in video_url:
                        video_id = video_url.split('youtu.be/')[1].split('?')[0]
                    elif 'v=' in video_url:
                        video_id = video_url.split('v=')[1].split('&')[0]
                    
                    logger.info(f"✅ Video published successfully!")
                    logger.info(f"🔗 URL: {video_url}")
                    logger.info(f"🆔 Video ID: {video_id}")
            except Exception as e:
                logger.warning(f"⚠️ Could not extract video URL: {e}")
                await page.screenshot(path='/tmp/youtube_url_extraction_error.png')
            
            # Take final screenshot
            await page.screenshot(path='/tmp/youtube_final_success.png')
            
            # Close browser
            await page.close()
            await self.context.close()
            await self.playwright.stop()
            self.context = None
            self.playwright = None
            
            return {
                "success": True,
                "platform": "youtube",
                "video_id": video_id,
                "url": video_url or "https://studio.youtube.com",
                "title": title,
                "privacy": privacy
            }
            
        except Exception as e:
            logger.error(f"❌ Upload failed: {e}")
            if page:
                try:
                    await page.screenshot(path='/tmp/youtube_error_final.png')
                    logger.info("📸 Error screenshot: /tmp/youtube_error_final.png")
                except:
                    pass
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
