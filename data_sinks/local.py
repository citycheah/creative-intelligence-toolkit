import os
import json
import logging
import pandas as pd
from datetime import datetime
from .base import BaseSink

logger = logging.getLogger(__name__)

class LocalCSVSink(BaseSink):
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def upload(self, df: pd.DataFrame) -> None:
        if df.empty:
            logger.info("LocalCSVSink: DataFrame is empty, nothing to export.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.output_dir, f"intel_report_{timestamp}.csv")
        
        # We might have dicts/lists in some columns, let's cast them to string for CSV compatibility
        export_df = df.copy()
        for col in export_df.columns:
            export_df[col] = export_df[col].apply(
                lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x
            )
            
        export_df.to_csv(filename, index=False)
        logger.info(f"LocalCSVSink: Successfully exported {len(df)} rows to {filename}")
