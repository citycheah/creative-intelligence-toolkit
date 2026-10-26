import sys
import os
import pandas as pd
from pydantic import BaseModel
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from creative_ai_analyzer import CreativeAnalyzer

# 1. Define a custom response schema using Pydantic
class VideoClassification(BaseModel):
    brand_name: str
    has_text_overlay: bool
    dominant_color: str
    creative_concept: str

def main():
    # Load environment variables from .env file if it exists
    load_dotenv()

    # 2. Define custom system instructions for Gemini
    system_instruction = """
    You are an expert creative analyst. Inspect the visual asset.
    Extract the following details:
    - BRAND NAME: The brand advertised or displayed. If none, write 'Generic'.
    - HAS TEXT OVERLAY: True if there is text superimposed on the video/image.
    - DOMINANT COLOR: The single most dominant color.
    - CREATIVE CONCEPT: Describe the main theme or creative hook of the video/image in one sentence.
    
    Provide your output in JSON format adhering strictly to the schema.
    """
    
    # 3. Initialize the Gemini Client
    # Mode A: Google AI Studio (API Key)
    # This automatically picks up the GEMINI_API_KEY environment variable if set.
    if os.environ.get("GEMINI_API_KEY"):
        print("Using Google AI Studio client (API key detected)...")
        client = genai.Client()
    # Mode B: Vertex AI (GCP)
    else:
        project = os.environ.get("GCP_PROJECT_ID")
        location = os.environ.get("GCP_LOCATION")
        if not project or not location:
            raise ValueError("GCP_PROJECT_ID and GCP_LOCATION must be set in environment variables for Vertex AI mode.")
        print(f"Using Vertex AI client (GCP project: {project}, location: {location})...")
        client = genai.Client(
            vertexai=True,
            project=project,
            location=location
        )
    
    # 4. Initialize the analyzer
    analyzer = CreativeAnalyzer(
        client=client,
        system_instruction=system_instruction,
        response_schema=VideoClassification,
        max_workers=2
    )

    # 4. Prepare data
    # CreativeAnalyzer supports HTTP URLs, GCS URIs (gs://), and local file paths.
    data = {
        "id": ["test_01"],
        "asset_path": ["downloaded_assets/ZCJUkyzr3Ac.mp4"],
        "channel": ["youtube"]
    }
    df = pd.DataFrame(data)
    
    print("Starting AI analysis on DataFrame...")
    result_df = analyzer.analyze_dataframe(df, path_col="asset_path")
    
    print("\n--- Analysis Results ---")
    print(result_df.to_string())

if __name__ == "__main__":
    main()
