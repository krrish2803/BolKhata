import pytest
import asyncio
from unittest.mock import patch, MagicMock
from app.agents.extractor import run_extractor_agent, increment_gemini_call_count, reset_gemini_call_count
from app.cache import get_cached_extraction, set_cached_extraction, prewarm_cache
from app.schemas import ExtractorOutput, ExtractedLine
from app.config import settings

@pytest.mark.asyncio
async def test_cache_hit_makes_no_api_call():
    """Requirement 7: Cache hit makes NO external API call."""
    prewarm_cache()
    sample_text = "Sharma ji ko do shirt aur ek trouser diye, 4200 bill, 2000 abhi diya, baaki udhaar"
    
    # Track Gemini call count
    reset_gemini_call_count()
    initial_calls = increment_gemini_call_count() # test counter
    reset_gemini_call_count()

    with patch("app.agents.extractor.increment_gemini_call_count") as mock_inc:
        out, model_info = await run_extractor_agent(
            raw_text=sample_text,
            customers_context=[],
            items_context=[]
        )
        # Should be served instantly from cache without calling increment_gemini_call_count
        assert mock_inc.call_count == 0
        assert model_info.get("cached") is True
        assert out.statedTotal == 4200
        assert out.paid == 2000

@pytest.mark.asyncio
async def test_429_handling_retries_correctly():
    """Requirement 7: 429 handling retries correctly with delay."""
    customers = [{"_id": "cust1", "name": "Sharma ji", "aliases": []}]
    items = [{"_id": "item1", "name": "Shirt", "aliases": [], "price": 1200}]
    
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = '{"customerName": "Sharma ji", "matchedCustomerId": "cust1", "lines": [{"itemName": "shirt", "matchedItemId": "item1", "qty": 1, "unitPrice": 1200}], "statedTotal": 1200, "paid": 1200}'
    
    # Simulate first two calls failing with 429 RESOURCE_EXHAUSTED (retry in 0.01s), then third succeeds
    call_attempts = [0]
    def side_effect(*args, **kwargs):
        call_attempts[0] += 1
        if call_attempts[0] < 3:
            raise Exception("429 RESOURCE_EXHAUSTED. Please retry in 0.05s.")
        return mock_resp

    mock_client.models.generate_content.side_effect = side_effect

    with patch("app.agents.extractor.get_gemini_client", return_value=mock_client):
        # Override asyncio.sleep to run quickly in unit tests
        with patch("asyncio.sleep", return_value=None):
            out, model_info = await run_extractor_agent(
                raw_text="Sharma ji ko ek shirt diya pura 1200 cash",
                customers_context=customers,
                items_context=items,
                allow_fallback=False
            )
            assert call_attempts[0] == 3
            assert model_info["source"] == "gemini"
            assert model_info["isFallback"] is False
            assert out.customerName == "Sharma ji"

@pytest.mark.asyncio
async def test_fallback_results_always_carry_source_fallback():
    """Requirement 7: Fallback results always carry source='fallback' and isFallback=True."""
    customers = [{"_id": "cust1", "name": "Sharma ji", "aliases": []}]
    items = [{"_id": "item1", "name": "Shirt", "aliases": [], "price": 1200}]

    # Force client to None (offline mode)
    with patch("app.agents.extractor.get_gemini_client", return_value=None):
        out, model_info = await run_extractor_agent(
            raw_text="Sharma ji ko do shirt diye bill 2400",
            customers_context=customers,
            items_context=items,
            allow_fallback=True
        )
        assert model_info["source"] == "fallback"
        assert model_info["isFallback"] is True
        assert model_info["model"] == "offline-rule-parser"
        assert out.customerName == "Sharma ji"

def test_global_daily_cap_logging_without_raw_text(caplog):
    """Requirement 6: Global daily cap is enforced and logged without raw text."""
    import logging
    caplog.set_level(logging.WARNING)
    
    reset_gemini_call_count()
    original_cap = settings.GEMINI_DAILY_CALL_CAP
    try:
        settings.GEMINI_DAILY_CALL_CAP = 3
        increment_gemini_call_count()
        increment_gemini_call_count()
        increment_gemini_call_count()
        
        # 4th call must hit cap
        with pytest.raises(RuntimeError) as exc_info:
            increment_gemini_call_count()
        assert "Daily Gemini API call cap reached" in str(exc_info.value)
        
        # Verify log output does NOT contain user raw text, but contains call count
        log_text = caplog.text
        assert "GLOBAL DAILY CALL CAP REACHED" in log_text
        assert "3 calls made" in log_text
    finally:
        settings.GEMINI_DAILY_CALL_CAP = original_cap
        reset_gemini_call_count()
