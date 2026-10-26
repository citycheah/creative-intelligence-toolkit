import pytest
from social_asset_downloader.base import BaseDownloader
from social_asset_downloader.yt_dlp import YtDlpDownloader


def test_base_downloader_is_abstract():
    with pytest.raises(TypeError):
        BaseDownloader()


def test_ytdlp_downloader_init():
    downloader = YtDlpDownloader()
    assert downloader.format_opt == 'worst[vcodec!=none]/worst/best'

    custom_downloader = YtDlpDownloader(format_opt='bestvideo+bestaudio')
    assert custom_downloader.format_opt == 'bestvideo+bestaudio'
