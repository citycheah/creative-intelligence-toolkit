import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from social_asset_downloader import YtDlpDownloader, IgFbDownloader, TtShopDownloader

async def main():
    output_dir = "downloaded_assets"
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. YtDlpDownloader (General/YouTube/Facebook/TikTok)
    yt_downloader = YtDlpDownloader()
    yt_url = "https://www.youtube.com/watch?v=ZCJUkyzr3Ac"
    print(f"--- Testing YtDlpDownloader with URL: {yt_url} ---")
    local_path = await yt_downloader.download(yt_url, output_dir)
    print(f"Result path: {local_path}\n")

    # 2. IgFbDownloader (Instagram/Facebook via direct Playwright source extraction)
    ig_downloader = IgFbDownloader()
    ig_url = "https://www.instagram.com/p/DSgzXBYjpcJ/"
    print(f"--- Testing IgFbDownloader with URL: {ig_url} ---")
    ig_paths = await ig_downloader.download(ig_url, output_dir)
    print(f"Result paths: {ig_paths}\n")

    # 3. TtShopDownloader (TikTok via snaptik.app extraction)
    tt_downloader = TtShopDownloader()
    tt_url = "https://www.tiktok.com/@colgateph/video/7493813461302988050"
    print(f"--- Testing TtShopDownloader with URL: {tt_url} ---")
    tt_path = await tt_downloader.download(tt_url, output_dir)
    print(f"Result path: {tt_path}\n")

if __name__ == "__main__":
    asyncio.run(main())
