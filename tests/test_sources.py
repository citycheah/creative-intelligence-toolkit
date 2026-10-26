from unittest.mock import patch, MagicMock
import pytest
from social_intel_sources.base import BaseSource
from social_intel_sources.rss import GoogleAlertsSource
from social_intel_sources.apify import ApifyBaseSource, _get_dataset_id


def test_base_source_is_abstract():
    with pytest.raises(TypeError):
        BaseSource()


def test_google_alerts_source_init_dict():
    feeds = {"US": "https://example.com/feed1", "UK": "https://example.com/feed2"}
    source = GoogleAlertsSource(feeds=feeds, brand_label="Acme")
    assert source.feeds == feeds
    assert source.brand_label == "Acme"


def test_google_alerts_source_init_list():
    feeds = ["https://example.com/feed1", "https://example.com/feed2"]
    source = GoogleAlertsSource(feeds=feeds)
    assert "Market_1" in source.feeds
    assert "Market_2" in source.feeds
    assert source.feeds["Market_1"] == "https://example.com/feed1"


@patch("social_intel_sources.rss.feedparser.parse")
def test_google_alerts_source_fetch_data(mock_parse):
    mock_entry = MagicMock()
    mock_entry.id = "tag:google.com,2013:googlealerts/feed:123"
    mock_entry.title = "Acme launches new product"
    mock_entry.link = "https://example.com/article"
    mock_entry.published = "2026-10-26T12:00:00Z"
    mock_entry.content = [{"value": "<p>Acme has announced...</p>"}]

    mock_feed = MagicMock()
    mock_feed.entries = [mock_entry]
    mock_parse.return_value = mock_feed

    source = GoogleAlertsSource(feeds={"US": "https://example.com/feed"}, brand_label="Acme")
    data = source.fetch_data()

    assert len(data) == 1
    assert data[0]["source"] == "Google Alerts"
    assert data[0]["market"] == "US"
    assert data[0]["brand"] == "Acme"
    assert data[0]["title"] == "Acme launches new product"
    assert data[0]["text"] == "<p>Acme has announced...</p>"


def test_apify_base_source_requires_token():
    class DummyApifySource(ApifyBaseSource):
        def fetch_data(self):
            return []

    with pytest.raises(ValueError, match="Apify token is required"):
        DummyApifySource(token="")


def test_get_dataset_id_utility():
    assert _get_dataset_id(None) is None
    assert _get_dataset_id({"defaultDatasetId": "ds_123"}) == "ds_123"
    assert _get_dataset_id({"default_dataset_id": "ds_456"}) == "ds_456"

    class DummyObj:
        def __init__(self, dataset_id):
            self.defaultDatasetId = dataset_id

    assert _get_dataset_id(DummyObj("ds_789")) == "ds_789"
