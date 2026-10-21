import hashlib
import re
import logging
from typing import Optional, Tuple, Dict, Any
from app.schemas import ExtractorOutput, ExtractedLine

logger = logging.getLogger(__name__)

# In-memory LRU / dict cache: normalized_text_hash -> (ExtractorOutput, model_info)
_PARSED_CACHE: Dict[str, Tuple[ExtractorOutput, Dict[str, Any]]] = {}

def normalize_text(text: str) -> str:
    """Normalize input text: lowercase, remove punctuation, collapse extra whitespace."""
    t = text.lower().strip()
    t = re.sub(r'[^\w\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def get_text_hash(text: str) -> str:
    norm = normalize_text(text)
    return hashlib.sha256(norm.encode('utf-8')).hexdigest()

def get_cached_extraction(text: str) -> Optional[Tuple[ExtractorOutput, Dict[str, Any]]]:
    h = get_text_hash(text)
    hit = _PARSED_CACHE.get(h)
    if hit:
        logger.info(f"Extraction cache HIT for text hash {h[:8]}")
        extractor_out, model_info = hit
        # Return a copy with cached flag marked true
        cached_info = dict(model_info)
        cached_info["cached"] = True
        return extractor_out, cached_info
    return None

def sanitize_cache_output(output: ExtractorOutput) -> ExtractorOutput:
    """
    Ensure cached extractor output contains NO customer or item IDs,
    and NO workspace-specific database keys. Matching must happen purely
    after cache lookup against the caller's active workspace catalog.
    """
    clean_lines = []
    for line in output.lines:
        clean_lines.append(
            ExtractedLine(
                itemName=line.itemName,
                matchedItemId=None,  # Stripped! Never leak item ID across workspaces
                qty=line.qty,
                unitPrice=line.unitPrice
            )
        )
    return ExtractorOutput(
        customerName=output.customerName,
        matchedCustomerId=None,  # Stripped! Never leak customer ID across workspaces
        lines=clean_lines,
        statedTotal=output.statedTotal,
        paid=output.paid,
        notes=output.notes
    )

def set_cached_extraction(text: str, output: ExtractorOutput, model_info: Dict[str, Any]) -> None:
    h = get_text_hash(text)
    # Sanitize output before caching: strip all workspace IDs
    sanitized_output = sanitize_cache_output(output)
    
    # Store up to 500 items in memory
    if len(_PARSED_CACHE) > 500:
        first_key = next(iter(_PARSED_CACHE))
        _PARSED_CACHE.pop(first_key, None)
    _PARSED_CACHE[h] = (sanitized_output, model_info)
    logger.info(f"Cached sanitized extraction for text hash {h[:8]}")

def prewarm_cache():
    """
    Pre-warm cache with the sample sale sentence shown in the UI:
    'Sharma ji ko do shirt aur ek trouser diye, 4200 bill, 2000 abhi diya, baaki udhaar'
    so the demo's first click never needs an external API call.
    """
    sample_text = "Sharma ji ko do shirt aur ek trouser diye, 4200 bill, 2000 abhi diya, baaki udhaar"
    from app.schemas import ExtractedLine
    sample_output = ExtractorOutput(
        customerName="Sharma ji",
        matchedCustomerId=None, # will be linked during validation
        lines=[
            ExtractedLine(itemName="shirt", matchedItemId=None, qty=2, unitPrice=1200),
            ExtractedLine(itemName="trouser", matchedItemId=None, qty=1, unitPrice=1800),
        ],
        statedTotal=4200,
        paid=2000,
        notes="Prewarmed UI sample entry"
    )
    sample_model_info = {
        "source": "gemini",
        "model": "gemini-2.5-flash",
        "latencyMs": 0,
        "isFallback": False,
        "cached": True
    }
    set_cached_extraction(sample_text, sample_output, sample_model_info)
    logger.info("Pre-warmed extraction cache with UI sample sentence.")

# Automatically run prewarm on module import
prewarm_cache()
