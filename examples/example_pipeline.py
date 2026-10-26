import os
import sys
import logging
import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel
from google import genai

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from social_intel_sources import (
    ApifyFacebookSource,
    ApifyInstagramSource,
    ApifyTikTokSource,
    ApifyYouTubeSource,
    GoogleAlertsSource
)
from creative_ai_analyzer import CreativeAnalyzer
from data_sinks import LocalCSVSink, TeamsAlertSink, SlackAlertSink

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ==============================================================================
# CONFIGURATION: Define your target brand, handles, RSS feeds, and AI schema
# ==============================================================================
BRAND_NAME = "Spotify"

GOOGLE_ALERT_FEEDS = {
    "United States": "https://www.google.com/alerts/feeds/09091005997914897266/309457738440368291",
}

INSTAGRAM_HANDLES = {
    "United States": "spotify",
}

TIKTOK_HANDLES = {
    "United States": "spotify",
}

YOUTUBE_CHANNELS = {
    "United States": "https://www.youtube.com/c/spotify",
}

FACEBOOK_URLS = {
    "United States": "https://www.facebook.com/Spotify"
}

# Define expected AI response schema
class BrandIntelligenceResult(BaseModel):
    is_relevant: bool
    summary: str
    key_topics: list[str]


def main():
    load_dotenv()
    
    logger.info(f"=== 1. Data Extraction ({BRAND_NAME}) ===")
    sources = []
    
    # 1a. Google Alerts RSS Feeds
    if GOOGLE_ALERT_FEEDS:
        sources.append(GoogleAlertsSource(feeds=GOOGLE_ALERT_FEEDS, brand_label=BRAND_NAME))
    
    # 1b. Apify Social Scrapers
    apify_token = os.environ.get("APIFY_TOKEN")
    if apify_token:
        if FACEBOOK_URLS:
            sources.append(ApifyFacebookSource(token=apify_token, start_urls=FACEBOOK_URLS, brand_label=BRAND_NAME))
        if INSTAGRAM_HANDLES:
            sources.append(ApifyInstagramSource(token=apify_token, handles=INSTAGRAM_HANDLES, brand_label=BRAND_NAME))
        if TIKTOK_HANDLES:
            sources.append(ApifyTikTokSource(token=apify_token, profiles=TIKTOK_HANDLES, brand_label=BRAND_NAME))
        if YOUTUBE_CHANNELS:
            sources.append(ApifyYouTubeSource(token=apify_token, channels=YOUTUBE_CHANNELS, brand_label=BRAND_NAME))
    else:
        logger.warning("No APIFY_TOKEN found in environment. Skipping Apify sources.")
        
    raw_data = []
    for src in sources:
        raw_data.extend(src.fetch_data())
        
    if not raw_data:
        logger.warning("No data retrieved from any source. Exiting.")
        return
        
    df = pd.DataFrame(raw_data)
    logger.info(f"Total raw records fetched: {len(df)}")
    
    analyzed_df = df.copy()
    
    logger.info("=== 2. Creative AI Analysis ===")
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        client = genai.Client(api_key=api_key)
        
        system_instruction = f"""
            You are a Senior Marketing Intelligence Analyst for {BRAND_NAME}.
            Analyze the provided social media content or news updates for {BRAND_NAME}.
            Determine if the content is relevant to key marketing campaigns and summarize the core messaging.
        """
        
        analyzer = CreativeAnalyzer(
            client=client,
            system_instruction=system_instruction,
            response_schema=BrandIntelligenceResult
        )
        
        # Analyze the DataFrame, using the 'link' column to fetch media where available
        analyzed_df = analyzer.analyze_dataframe(df, path_col="link")
    else:
        logger.warning("No GEMINI_API_KEY found. Skipping AI analysis and proceeding with raw data export.")
        
    logger.info("=== 3. Export to Sinks ===")
    # Export locally to CSV
    local_sink = LocalCSVSink(output_dir="reports")
    local_sink.upload(analyzed_df)
            
    logger.info("=== 4. Dispatch Alerts ===")
    report_title = f"{BRAND_NAME} Intelligence Report"
    
    # Microsoft Teams Webhook
    teams_url = os.environ.get("TEAMS_WEBHOOK_URL")
    if teams_url:
        teams = TeamsAlertSink(webhook=teams_url, report_title=report_title, filter_col="is_relevant")
        teams.upload(analyzed_df)
        
    # Slack Webhook
    slack_url = os.environ.get("SLACK_WEBHOOK_URL")
    if slack_url:
        slack = SlackAlertSink(webhook=slack_url, report_title=report_title, filter_col="is_relevant")
        slack.upload(analyzed_df)
        
    logger.info("Pipeline execution complete.")

if __name__ == "__main__":
    main()
