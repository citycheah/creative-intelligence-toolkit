from unittest.mock import MagicMock
from pydantic import BaseModel
from creative_ai_analyzer.analyzer import CreativeAnalyzer


class DummyCreativeSchema(BaseModel):
    brand_name: str
    creative_format: str
    is_promo: bool


def test_creative_analyzer_initialization_fields():
    mock_client = MagicMock()
    mock_client.vertexai = False
    mock_client._api_client.api_key = "dummy_key"

    analyzer = CreativeAnalyzer(
        client=mock_client,
        system_instruction="Analyze the creative.",
        response_schema=DummyCreativeSchema,
        model="gemini-2.5-flash",
        chunk_size=50,
        max_workers=4
    )

    assert set(analyzer.ai_fields) == {"brand_name", "creative_format", "is_promo"}
    assert analyzer.chunk_size == 50
    assert analyzer.max_workers == 4
    assert analyzer.model == "gemini-2.5-flash"
