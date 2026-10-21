import logging
from typing import List, Dict, Any, Tuple
from app.agents.extractor import run_extractor_agent
from app.agents.validator import validate_extraction
from app.schemas import DraftResponse, DraftIssue, DraftLine

logger = logging.getLogger(__name__)

async def run_pipeline(
    raw_text: str,
    customers_catalog: List[Dict[str, Any]],
    items_catalog: List[Dict[str, Any]],
    allow_fallback: bool = True,
) -> Tuple[Dict[str, Any], List[DraftLine], List[DraftIssue], int, int, int, int, int, int, int, bool, Dict[str, Any]]:
    """
    Deterministic Agent Pipeline:
    1. ExtractorAgent: exactly ONE Gemini call by default.
    2. ValidatorAgent: runs all validation and catalog matching strictly in plain Python.
    3. Allow one extra extractor call ONLY when the validator returns a fixable ambiguity
       (e.g., missing/ambiguous customer or missing line items). Never call the model for arithmetic or stock warnings.
    """
    # Pass 1: Extraction (exactly ONE Gemini call by default)
    extracted, model_info = await run_extractor_agent(
        raw_text, customers_catalog, items_catalog, allow_fallback=allow_fallback
    )
    
    # Pass 1: Validation (plain Python)
    draft_lines, issues, list_price, discount, total, due, can_save = validate_extraction(
        extracted, items_catalog, customers_catalog, raw_text=raw_text
    )

    # Check for fixable ambiguity: ONLY missing customer or missing items
    # (Do NOT retry for price assumptions, high discounts, low stock, or math)
    fixable_ambiguity_codes = {"MISSING_CUSTOMER", "NO_ITEMS"}
    has_fixable_ambiguity = any(i.code in fixable_ambiguity_codes and i.severity == "error" for i in issues)
    
    if has_fixable_ambiguity:
        logger.info("Fixable ambiguity detected (missing customer/items), executing exactly ONE retry with issues attached")
        retry_issues = [f"{i.field}: {i.message}" for i in issues if i.code in fixable_ambiguity_codes]
        
        # Retry pass (Pass 2 - maximum 1 extra call)
        extracted_retry, model_info_retry = await run_extractor_agent(
            raw_text, customers_catalog, items_catalog, previous_issues=retry_issues, allow_fallback=allow_fallback
        )
        
        draft_lines_retry, issues_retry, list_price_retry, discount_retry, total_retry, due_retry, can_save_retry = validate_extraction(
            extracted_retry, items_catalog, customers_catalog, raw_text=raw_text
        )
        
        # Adopt retry if it fixed the ambiguity
        if sum(1 for i in issues_retry if i.code in fixable_ambiguity_codes) < sum(1 for i in issues if i.code in fixable_ambiguity_codes):
            extracted = extracted_retry
            model_info = model_info_retry
            draft_lines = draft_lines_retry
            issues = issues_retry
            list_price = list_price_retry
            discount = discount_retry
            total = total_retry
            due = due_retry
            can_save = can_save_retry

    # Build customer match summary
    customer_info = None
    if extracted.matchedCustomerId:
        matched_c = next((c for c in customers_catalog if str(c["_id"]) == extracted.matchedCustomerId), None)
        if matched_c:
            customer_info = {
                "id": str(matched_c["_id"]),
                "name": matched_c["name"],
                "phone": matched_c.get("phone"),
                "balance": matched_c.get("balance", 0),
                "isNew": False,
            }
    if not customer_info and extracted.customerName:
        customer_info = {
            "id": None,
            "name": extracted.customerName,
            "phone": None,
            "balance": 0,
            "isNew": True,
        }

    paid = extracted.paid if extracted.paid is not None else 0
    stated_total = extracted.statedTotal
    computed_total = list_price

    return customer_info, draft_lines, issues, stated_total, computed_total, list_price, discount, total, paid, due, can_save, model_info
