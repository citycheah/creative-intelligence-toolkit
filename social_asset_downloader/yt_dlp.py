import os
import asyncio
import logging
import yt_dlp
from .base import BaseDownloader

logger = logging.getLogger(__name__)

class YtDlpDownloader(BaseDownloader):
    """
    Downloads social media videos using the yt-dlp library.
    """
    def __init__(self, format_opt: str = 'worst[vcodec!=none]/worst/best'):
        """
        Args:
            format_opt (str): The format selection string for yt-dlp.
                              Defaults to downloading the lowest quality video to save bandwidth.
        """
        self.format_opt = format_opt

    async def download(self, url: str, output_dir: str) -> str | None:
        """
        Asynchronously downloads a video to the specified directory.
        """
        return await asyncio.to_thread(self._download_sync, url, output_dir)

    def _download_sync(self, url: str, output_dir: str) -> str | None:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        ydl_opts = {
            'format': self.format_opt,
            'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                downloaded_file_path = ydl.prepare_filename(info_dict)
                
                if downloaded_file_path and os.path.exists(downloaded_file_path):
                    # Exclude audio-only formats if they are not wanted
                    if downloaded_file_path.lower().endswith(('.mp3', '.m4a', '.wav', '.flac', '.ogg', '.aac')):
                        os.remove(downloaded_file_path)
                        return None
                    return downloaded_file_path
        except Exception as e:
            logger.error(f"yt-dlp download failed for {url}: {e}")
        return None
