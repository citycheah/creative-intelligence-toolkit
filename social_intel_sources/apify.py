import logging
from apify_client import ApifyClient
from .base import BaseSource

logger = logging.getLogger(__name__)

def _get_dataset_id(run_result: any) -> str | None:
    if not run_result:
        return None
    if isinstance(run_result, dict):
        return run_result.get("defaultDatasetId") or run_result.get("default_dataset_id")
    return getattr(run_result, "default_dataset_id", getattr(run_result, "defaultDatasetId", None))


class ApifyBaseSource(BaseSource):
    """Base class for all Apify-powered sources."""
    def __init__(self, token: str, brand_label: str | None = None):
        if not token:
            raise ValueError("Apify token is required")
        self.client = ApifyClient(token)
        self.brand_label = brand_label


class ApifyFacebookSource(ApifyBaseSource):
    """Scrapes Facebook posts via Apify actor 'apify/facebook-posts-scraper'."""
    def __init__(self, token: str, start_urls: list[str] | list[dict] | dict[str, str], only_newer_than: str = "1 day", brand_label: str | None = None):
        super().__init__(token=token, brand_label=brand_label)
        self.only_newer_than = only_newer_than
        
        if isinstance(start_urls, dict):
            self.start_urls = [{"url": url} for url in start_urls.values()]
        elif isinstance(start_urls, list):
            self.start_urls = [{"url": u} if isinstance(u, str) else u for u in start_urls]
        else:
            self.start_urls = []

    def fetch_data(self) -> list[dict]:
        data_points = []
        logger.info("Checking Apify: Facebook Posts Scraper...")
        try:
            facebook_posts = self.client.actor("apify/facebook-posts-scraper").call(
                run_input={
                    "startUrls": self.start_urls,
                    "onlyPostsNewerThan": self.only_newer_than
                }
            )
            dataset_id = _get_dataset_id(facebook_posts)
            if not dataset_id:
                logger.warning("No dataset_id returned from Facebook scraper.")
                return data_points
            for item in self.client.dataset(dataset_id).iterate_items():
                post_id = item.get('postId') or item.get('id')
                link = item.get('url') or item.get('postUrl')
                text = item.get('text') or item.get('message')

                # Skip empty/metadata-only items
                if not (post_id or link or text):
                    continue

                extracted_media = {}
                images = []
                for i, m in enumerate(item.get("media", [])):
                    if isinstance(m, dict):
                        media_type = m.get("__typename") or m.get("__isMedia")
                        if i == 0 and m.get("thumbnail"):
                            extracted_media["thumbnail"] = m.get("thumbnail")
                        if media_type == "Photo":
                            image_uri = m.get("image", {}).get("uri")
                            if image_uri:
                                images.append(image_uri)
                        elif media_type == "Video":
                            video_delivery = m.get("videoDeliveryLegacyFields", {})
                            video_url = video_delivery.get("browser_native_sd_url") or m.get("permalink_url")
                            if video_url:
                                extracted_media["video_url"] = video_url
                if images:
                    extracted_media["images"] = images

                dp = {
                    "source": "Facebook",
                    "market": "Global",
                    "id": post_id,
                    "link": link,
                    "media": extracted_media,
                    "published": item.get('time') or item.get('date'),
                    "text": text
                }
                if self.brand_label:
                    dp["brand"] = self.brand_label
                data_points.append(dp)
        except Exception as e:
            logger.warning(f"Failed to scrape Facebook: {e}")
        return data_points


class ApifyInstagramSource(ApifyBaseSource):
    """Scrapes Instagram posts via Apify actor 'apify/instagram-post-scraper'."""
    def __init__(self, token: str, handles: dict[str, str] | list[str], only_newer_than: str = "1 day", brand_label: str | None = None):
        super().__init__(token=token, brand_label=brand_label)
        self.only_newer_than = only_newer_than
        
        if isinstance(handles, list):
            self.handles = {f"Market_{i+1}": h for i, h in enumerate(handles)}
        else:
            self.handles = handles

    def fetch_data(self) -> list[dict]:
        data_points = []
        for market, handle in self.handles.items():
            logger.info(f"Checking Apify: Instagram Post Scraper for {market} ({handle})...")
            try:
                username_url = handle if handle.startswith("http") else f"https://www.instagram.com/{handle}/"
                result = self.client.actor("apify/instagram-post-scraper").call(
                    run_input={
                        "username": [username_url],
                        "skipPinnedPosts": True,
                        "onlyPostsNewerThan": self.only_newer_than
                    }
                )
                dataset_id = _get_dataset_id(result)
                if not dataset_id:
                    logger.warning(f"No dataset_id returned from Instagram scraper for {market}.")
                    continue
                for item in self.client.dataset(dataset_id).iterate_items():
                    post_id = item.get('id') or item.get('shortCode')
                    link = item.get('url')
                    caption = item.get('caption')

                    # Skip empty metadata items
                    if not (post_id or link or caption):
                        continue

                    extracted_media = {}
                    if item.get('displayUrl'):
                        extracted_media["thumbnail"] = item.get('displayUrl')
                    if item.get('images'):
                        extracted_media['images'] = item.get('images')
                    if item.get('videoUrl'):
                        extracted_media['video_url'] = item.get('videoUrl')

                    dp = {
                        "source": "Instagram",
                        "market": market,
                        "id": post_id,
                        "link": link,
                        "media": extracted_media,
                        "published": item.get('timestamp'),
                        "text": caption
                    }
                    if self.brand_label:
                        dp["brand"] = self.brand_label
                    data_points.append(dp)
            except Exception as e:
                logger.warning(f"Failed to scrape Instagram for {market}: {e}")
        return data_points


class ApifyTikTokSource(ApifyBaseSource):
    """Scrapes TikTok profiles via Apify actor 'clockworks/tiktok-profile-scraper'."""
    def __init__(self, token: str, profiles: dict[str, str] | list[str], oldest_post_date: str = "1 day", brand_label: str | None = None):
        super().__init__(token=token, brand_label=brand_label)
        self.oldest_post_date = oldest_post_date
        
        if isinstance(profiles, list):
            self.profiles = {f"Market_{i+1}": p for i, p in enumerate(profiles)}
        else:
            self.profiles = profiles

    def fetch_data(self) -> list[dict]:
        data_points = []
        for market, profile in self.profiles.items():
            logger.info(f"Checking Apify: TikTok Profile Scraper for {market} ({profile})...")
            try:
                result = self.client.actor("clockworks/tiktok-profile-scraper").call(
                    run_input={
                        "profiles": [profile],
                        "excludePinnedPosts": True,
                        "oldestPostDateUnified": self.oldest_post_date,
                        "shouldDownloadVideos": True,
                        "shouldDownloadSlideshowImages": True
                    }
                )
                dataset_id = _get_dataset_id(result)
                if not dataset_id:
                    logger.warning(f"No dataset_id returned from TikTok scraper for {market}.")
                    continue
                for item in self.client.dataset(dataset_id).iterate_items():
                    video_id = item.get('id')
                    link = item.get('webVideoUrl')
                    text = item.get('text')

                    if not (video_id or link or text):
                        continue

                    extracted_media = {}
                    video_meta = item.get("videoMeta", {})
                    if video_meta.get("coverUrl"):
                        extracted_media["thumbnail"] = video_meta.get("coverUrl")

                    if item.get("isSlideshow"):
                        extracted_media["images"] = [img.get("downloadLink") for img in item.get("slideshowImageLinks", []) if img.get("downloadLink")]
                    elif video_meta.get("downloadAddr"):
                        extracted_media["video_url"] = video_meta.get("downloadAddr")

                    dp = {
                        "source": "TikTok",
                        "market": market,
                        "id": video_id,
                        "link": link,
                        "media": extracted_media,
                        "published": item.get('createTimeISO'),
                        "text": text
                    }
                    if self.brand_label:
                        dp["brand"] = self.brand_label
                    data_points.append(dp)
            except Exception as e:
                logger.warning(f"Failed to scrape TikTok for {market}: {e}")
        return data_points


class ApifyYouTubeSource(ApifyBaseSource):
    """Scrapes YouTube channels via Apify actor 'streamers/youtube-channel-scraper'."""
    def __init__(self, token: str, channels: dict[str, str] | list[str], oldest_post_date: str = "1 day", brand_label: str | None = None):
        super().__init__(token=token, brand_label=brand_label)
        self.oldest_post_date = oldest_post_date
        
        if isinstance(channels, list):
            self.channels = {f"Market_{i+1}": c for i, c in enumerate(channels)}
        else:
            self.channels = channels

    def fetch_data(self) -> list[dict]:
        data_points = []
        for market, channel in self.channels.items():
            logger.info(f"Checking Apify: YouTube Scrapers for {market} ({channel})...")
            try:
                result = self.client.actor("streamers/youtube-scraper").call(
                    run_input={
                        "startUrls": [{"url": channel}],
                        "oldestPostDate": self.oldest_post_date,
                        "lengthFilter": "under4",
                        "maxResults": 10,
                    }
                )
                dataset_id = _get_dataset_id(result)
                if not dataset_id:
                    logger.warning(f"No dataset_id returned from YouTube scraper for {market}.")
                    continue
                for item in self.client.dataset(dataset_id).iterate_items():
                    # Filter out non-video entries (e.g. channel info or about items)
                    item_type = item.get('type')
                    if item_type and item_type != 'video':
                        continue

                    video_id = item.get('id')
                    video_url = item.get('url')
                    title = item.get('title')
                    text = item.get('text')

                    # Skip channel landing page metadata or items lacking video ID/title
                    if not (video_id or title):
                        continue

                    extracted_media = {}
                    if item.get('thumbnailUrl'):
                        extracted_media["thumbnail"] = item.get('thumbnailUrl')
                    
                    dp = {
                        "source": "YouTube",
                        "market": market,
                        "id": video_id,
                        "link": video_url,
                        "media": extracted_media,
                        "published": item.get('date'),
                        "title": title,
                        "text": text
                    }
                    if self.brand_label:
                        dp["brand"] = self.brand_label
                    data_points.append(dp)
            except Exception as e:
                logger.warning(f"Failed to scrape YouTube for {market}: {e}")
        return data_points
