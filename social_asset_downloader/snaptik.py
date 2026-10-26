import os
import hashlib
import logging
from playwright.async_api import async_playwright, BrowserContext
from playwright_stealth import Stealth
import httpx
from .base import BaseDownloader

logger = logging.getLogger(__name__)

class TtShopDownloader(BaseDownloader):
    """
    Downloads TikTok videos without watermarks using snaptik.app.
    """
    def __init__(self, browser_context: BrowserContext = None):
        """
        Args:
            browser_context (BrowserContext, optional): An existing Playwright BrowserContext.
                                                        If not provided, a new browser instance will be launched.
        """
        self.browser_context = browser_context

    async def download(self, url: str, output_dir: str) -> str | None:
        """
        Asynchronously downloads a TikTok video without watermarks using Snaptik.
        
        Returns:
            str | None: The local file path of the downloaded video, or None if failed.
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        if self.browser_context:
            return await self._download_with_context(self.browser_context, url, output_dir)
        else:
            async with Stealth().use_async(async_playwright()) as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080}
                )
                res = await self._download_with_context(context, url, output_dir)
                await browser.close()
                return res

    async def _download_with_context(self, context: BrowserContext, url: str, output_dir: str) -> str | None:
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:12]
        filename = f"{url_hash}_snaptik.mp4"
        file_path = os.path.join(output_dir, filename)

        success = await self._trigger_snaptik_download(page, url, file_path)
        await page.close()

        return file_path if success else None

    async def _trigger_snaptik_download(self, page, tiktok_url: str, dest_path: str) -> bool:
        try:
            await page.goto("https://snaptik.app/", timeout=20000)
            await page.wait_for_selector('input[name="url"]', timeout=10000)
            await page.fill('input[name="url"]', tiktok_url)
            await page.click('button[type="submit"]')

            selectors = [
                'button:has-text("Download (No Watermark)")',
                'a.button.download-file',
                'a:has-text("Download (No Watermark)")'
            ]
            
            combined_selector = ", ".join(selectors)
            await page.wait_for_selector(combined_selector, timeout=15000)
            
            for sel in selectors:
                el = await page.query_selector(sel)
                if el:
                    tag_name = await el.evaluate("el => el.tagName.toLowerCase()")
                    if tag_name == 'a':
                        href = await el.get_attribute("href")
                        if href and not href.startswith("#") and not href.startswith("javascript:"):
                            return await self._download_file(href, dest_path)
            
            async with page.expect_download(timeout=20000) as download_info:
                for sel in selectors:
                    try:
                        await page.click(sel, timeout=3000)
                        break
                    except Exception:
                        continue
            
            download = await download_info.value
            await download.save_as(dest_path)
            return os.path.exists(dest_path)
            
        except Exception as e:
            logger.error(f"Error downloading from Snaptik: {e}")
            return False

    async def _download_file(self, download_url: str, dest_path: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(download_url)
                if response.status_code == 200:
                    with open(dest_path, 'wb') as f:
                        f.write(response.content)
                    return True
                else:
                    logger.error(f"Failed to download video from {download_url}, status code: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Failed to download file from Snaptik: {e}")
            return False
