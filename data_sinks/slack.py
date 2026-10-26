import json
import logging
import requests
import pandas as pd
from datetime import datetime
from .base import BaseSink

logger = logging.getLogger(__name__)

class SlackAlertSink(BaseSink):
    """
    Generic Slack Alert Sink.
    Pushes Markdown intelligence reports via webhook.
    """
    def __init__(self, webhook: str, report_title: str = "Social Media Intelligence Report", filter_col: str | None = None):
        if not webhook:
            raise ValueError("webhook URL is required for SlackAlertSink")
        self.webhook_url = webhook
        self.report_title = report_title
        self.filter_col = filter_col

    def _format_source(self, df_source: pd.DataFrame, source_name: str) -> str:
        if df_source.empty:
            return f"_(No updates for {source_name} today)_"

        texts = []
        for _, d in df_source.iterrows():
            thumb = "N/A"
            if isinstance(d.get("media"), dict):
                thumb = d.get("media", {}).get("thumbnail", "N/A")
            
            link = d.get('link', 'N/A')
            title_or_text = str(d.get('text', d.get('title', 'N/A')))[:1000]
            summary = d.get('summary', '')
            
            item_str = f"*Market:* {d.get('market', 'Global')}  \n*ID:* {d.get('id', 'N/A')}  \n*Link:* {link}  \n*Thumbnail:* {thumb}  \n*Text:* {title_or_text}"
            if summary:
                item_str += f"  \n*AI Summary:* {summary}"
            texts.append(item_str)
            
        return "\n\n---\n\n".join(texts)

    def upload(self, df: pd.DataFrame) -> None:
        if df.empty:
            logger.info("SlackAlertSink: DataFrame is empty, nothing to alert.")
            return

        target_df = df
        if self.filter_col and self.filter_col in df.columns:
            target_df = df[df[self.filter_col] == True]

        if target_df.empty:
            logger.info(f"SlackAlertSink: No matching rows found for filter column '{self.filter_col}'. Skipping alert.")
            return

        for source_name, group_df in target_df.groupby('source'):
            items_markdown = self._format_source(group_df, source_name)
            
            header = f"*{self.report_title}: {source_name}*\n_Data retrieved on: {datetime.now().strftime('%Y-%m-%d')}_\n\n"
            
            payload = {
                "text": header + items_markdown
            }

            logger.info(f"Dispatching alert to Slack for {source_name}...")
            try:
                response = requests.post(
                    self.webhook_url,
                    data=json.dumps(payload),
                    headers={'Content-Type': 'application/json'}
                )
                if response.status_code == 200 or response.text.lower() == "ok":
                    logger.info(f"Successfully posted {source_name} to Slack.")
                else:
                    logger.error(f"Failed to post to Slack. Status: {response.status_code}, Response: {response.text}")
            except Exception as e:
                logger.error(f"Error connecting to Slack webhook: {str(e)}")
