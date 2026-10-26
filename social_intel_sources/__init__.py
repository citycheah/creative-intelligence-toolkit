# Package exposing intelligence sources
from .base import BaseSource
from .rss import GoogleAlertsSource

try:
    from .apify import (
        ApifyBaseSource,
        ApifyFacebookSource,
        ApifyInstagramSource,
        ApifyTikTokSource,
        ApifyYouTubeSource,
    )
except ImportError:
    ApifyBaseSource = None
    ApifyFacebookSource = None
    ApifyInstagramSource = None
    ApifyTikTokSource = None
    ApifyYouTubeSource = None

__all__ = [
    "BaseSource",
    "GoogleAlertsSource",
    "ApifyBaseSource",
    "ApifyFacebookSource",
    "ApifyInstagramSource",
    "ApifyTikTokSource",
    "ApifyYouTubeSource",
]
