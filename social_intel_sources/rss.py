import logging
import feedparser
from .base import BaseSource

logger = logging.getLogger(__name__)

class GoogleAlertsSource(BaseSource):
    """
    Google Alerts RSS feed source.
    Accepts a dictionary mapping market/label to Google Alerts feed URLs (e.g. {"US": "https://www.google.com/alerts/feeds/..."}),
    or a list of feed URLs.
    """
    def __init__(self, feeds: dict[str, str] | list[str], brand_label: str | None = None):
        if isinstance(feeds, list):
            self.feeds = {f"Market_{i+1}": url for i, url in enumerate(feeds)}
        else:
            self.feeds = feeds
        self.brand_label = brand_label

    def fetch_data(self) -> list[dict]:
        data_points = []
        logger.info("Checking Google Alerts RSS feeds...")
        for label, url in self.feeds.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    # Extract raw HTML string value from feedparser content list
                    text_val = ""
                    content = getattr(entry, "content", None)
                    if content and isinstance(content, list) and len(content) > 0 and isinstance(content[0], dict):
                        text_val = content[0].get("value", "")
                    
                    if not text_val:
                        text_val = getattr(entry, "summary", getattr(entry, "title", ""))

                    item = {
                        "source": "Google Alerts",
                        "market": label,
                        "id": getattr(entry, "id", ""),
                        "title": getattr(entry, "title", ""),
                        "link": getattr(entry, "link", ""),
                        "published": getattr(entry, "published", None),
                        "text": text_val,
                    }
                    if self.brand_label:
                        item["brand"] = self.brand_label
                    data_points.append(item)
            except Exception as e:
                logger.warning(f"Failed to fetch Google Alerts for {label}: {e}")
        return data_points
