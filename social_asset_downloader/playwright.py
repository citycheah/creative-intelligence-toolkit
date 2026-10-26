import asyncio
import re
import json
import os
import logging
import urllib.request
import hashlib
from playwright.async_api import async_playwright, BrowserContext
from playwright_stealth import Stealth
from .base import BaseDownloader

logger = logging.getLogger(__name__)

class IgFbDownloader(BaseDownloader):
    """
    Downloads media from Instagram and Facebook posts by parsing the page source via Playwright.
    """
    def __init__(self, browser_context: BrowserContext = None):
        """
        Args:
            browser_context (BrowserContext, optional): An existing Playwright BrowserContext.
                                                        If not provided, a new browser instance will be launched.
        """
        self.browser_context = browser_context

    async def download(self, url: str, output_dir: str) -> list[str] | None:
        """
        Asynchronously downloads all media from the given Instagram or Facebook URL.
        
        Returns:
            list[str] | None: A list of local file paths of the downloaded assets, or None if failed.
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

    async def _download_with_context(self, context: BrowserContext, url: str, output_dir: str) -> list[str] | None:
        source = await self._fetch_page_source(context, url)
        if not source:
            return None

        video_url = self._extract_video_url(source)
        photo_urls = self._extract_photo_urls(source)
        fb_photo_urls = self._extract_fb_photo_urls(source)

        media_urls_to_download = []
        is_video = False

        if video_url:
            media_urls_to_download = [video_url]
            is_video = True
        elif photo_urls:
            media_urls_to_download = photo_urls
        elif fb_photo_urls:
            media_urls_to_download = fb_photo_urls

        if not media_urls_to_download:
            logger.warning(f"No media URLs found in source for {url}")
            return None

        downloaded_paths = []
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:12]

        for i, m_url in enumerate(media_urls_to_download):
            ext = 'mp4' if is_video else 'jpg'
            filename = f"{url_hash}_{i}.{ext}"
            file_path = os.path.join(output_dir, filename)

            success = await self._download_file(m_url, file_path)
            if success:
                downloaded_paths.append(file_path)

        return downloaded_paths if downloaded_paths else None

    async def _fetch_page_source(self, context: BrowserContext, url: str) -> str | None:
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        view_source_url = f"view-source:{url}"
        try:
            await page.goto(view_source_url, wait_until="domcontentloaded", timeout=20000)
            source_text = await page.inner_text("body")
            return source_text
        except Exception as e:
            logger.error(f"Error occurred during navigation to {url}: {e}")
            return None
        finally:
            await page.close()

    async def _download_file(self, media_url: str, dest_path: str) -> bool:
        try:
            await asyncio.to_thread(self._urllib_download, media_url, dest_path)
            return os.path.exists(dest_path)
        except Exception as e:
            logger.error(f"Failed to download media {media_url}: {e}")
            return False

    def _urllib_download(self, url: str, dest: str):
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        with urllib.request.urlopen(req, timeout=15) as response, open(dest, 'wb') as out_file:
            out_file.write(response.read())

    def _extract_video_url(self, source_text: str) -> str | None:
        if not source_text:
            return None
        match = re.search(r'"video_versions"\s*:\s*\[\s*\{.*?"url"\s*:\s*"([^"]+)"', source_text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            raw_url = match.group(1)
            try:
                return json.loads(f'"{raw_url}"')
            except json.JSONDecodeError:
                return raw_url.replace(r'\/', '/').replace(r'\u0026', '&')
        return None

    def _extract_photo_urls(self, source_text: str) -> list[str]:
        if not source_text:
            return []
        urls = []
        matches = re.finditer(r'"image_versions2"\s*:\s*\{\s*"candidates"\s*:\s*\[\s*\{([^{]*?)"url"\s*:\s*"([^"]+)"', source_text, flags=re.IGNORECASE | re.DOTALL)
        for match in matches:
            between_text = match.group(1)
            if 'height' in between_text:
                continue
            raw_url = match.group(2)
            try:
                clean_url = json.loads(f'"{raw_url}"')
                urls.append(clean_url)
            except json.JSONDecodeError:
                urls.append(raw_url.replace(r'\/', '/').replace(r'\u0026', '&'))
        return list(set(urls))

    def _extract_fb_photo_urls(self, source_text: str) -> list[str]:
        if not source_text:
            return []
        urls = []
        pattern1 = r'"photo_image"\s*:\s*\{\s*"uri"\s*:\s*"([^"]+)"'
        pattern2 = r'"__typename"\s*:\s*"Photo".{0,150}?"image"\s*:\s*\{\s*"uri"\s*:\s*"([^"]+)"'
        matches1 = re.finditer(pattern1, source_text, flags=re.IGNORECASE | re.DOTALL)
        matches2 = re.finditer(pattern2, source_text, flags=re.IGNORECASE | re.DOTALL)
        for match in list(matches1) + list(matches2):
            raw_url = match.group(1)
            try:
                clean_url = json.loads(f'"{raw_url}"')
                urls.append(clean_url)
            except json.JSONDecodeError:
                urls.append(raw_url.replace(r'\/', '/').replace(r'\u0026', '&'))
        return list(set(urls))
