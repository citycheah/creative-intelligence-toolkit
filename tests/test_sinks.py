import os
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from data_sinks.base import BaseSink
from data_sinks.local import LocalCSVSink
from data_sinks.slack import SlackAlertSink
from data_sinks.teams import TeamsAlertSink


def test_base_sink_is_abstract():
    with pytest.raises(TypeError):
        BaseSink()


def test_local_csv_sink(tmp_path):
    output_dir = str(tmp_path / "reports")
    sink = LocalCSVSink(output_dir=output_dir)

    df = pd.DataFrame({
        "brand": ["Spotify", "Apple"],
        "reach": [1000, 2000]
    })
    sink.upload(df)

    files = os.listdir(output_dir)
    assert len(files) == 1
    assert files[0].startswith("intel_report_")
    assert files[0].endswith(".csv")

    loaded_df = pd.read_csv(os.path.join(output_dir, files[0]))
    assert len(loaded_df) == 2
    assert "brand" in loaded_df.columns


def test_slack_sink_requires_webhook():
    with pytest.raises(ValueError, match="webhook URL is required"):
        SlackAlertSink(webhook="")


def test_slack_sink_format_source():
    sink = SlackAlertSink(webhook="https://hooks.slack.com/services/dummy")
    df = pd.DataFrame([
        {
            "market": "US",
            "id": "post_101",
            "link": "https://example.com/ad",
            "text": "Check out our newest campaign!",
            "summary": "AI classified as promotional",
            "source": "Instagram"
        }
    ])

    formatted = sink._format_source(df, "Instagram")
    assert "*Market:* US" in formatted
    assert "*ID:* post_101" in formatted
    assert "*AI Summary:* AI classified as promotional" in formatted


def test_teams_sink_requires_webhook():
    with pytest.raises(ValueError, match="webhook URL is required"):
        TeamsAlertSink(webhook="")


def test_teams_sink_format_source():
    sink = TeamsAlertSink(webhook="https://outlook.office.com/webhook/dummy")
    df = pd.DataFrame([
        {
            "market": "Global",
            "id": "vid_202",
            "link": "https://example.com/video",
            "title": "Exciting product reveal",
            "summary": "High energy hook",
            "source": "TikTok"
        }
    ])

    formatted = sink._format_source(df, "TikTok")
    assert "**Market:** Global" in formatted
    assert "**ID:** vid_202" in formatted
    assert "**AI Summary:** High energy hook" in formatted
