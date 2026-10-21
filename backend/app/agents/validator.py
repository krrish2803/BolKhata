import re
from difflib import SequenceMatcher
from typing import List, Dict, Any, Tuple, Optional
from app.schemas import ExtractorOutput, DraftIssue, DraftLine
from app.accounting import compute_line_total

QTY_WORDS_MAP = {
    "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4,
    "paanch": 5, "panch": 5, "chhe": 6, "che": 6, "chha": 6,
    "saat": 7, "sat": 7, "aath": 8, "ath": 8, "nau": 9, "das": 10,
    "gyarah": 11, "barah": 12, "terah": 13, "chaudah": 14, "pandrah": 15,
    "solah": 16, "satrah": 17, "atharah": 18, "unnis": 19, "bees": 20,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

def _fuzzy_word_in_text(name_or_word: str, input_text: str, threshold: float = 0.65) -> bool:
    """Check if any word in name_or_word fuzzy matches a word in input_text."""
    if not name_or_word or not input_text:
        return False
    name_tokens = re.findall(r'[a-zA-Z0-9]+', name_or_word.lower())
    # Ignore generic honorifics when matching customer name
    meaningful_tokens = [t for t in name_tokens if t not in {'ji', 'sir', 'saab', 'bhai', 'ko', 'ne', 'cloth', 'hardware', 'tailor'}]
    if not meaningful_tokens:
        meaningful_tokens = name_tokens
    
    text_tokens = re.findall(r'[a-zA-Z0-9]+', input_text.lower())
    for ntok in meaningful_tokens:
        for ttok in text_tokens:
            if ntok in ttok or ttok in ntok:
                return True
            ratio = SequenceMatcher(None, ntok, ttok).ratio()
            if ratio >= threshold:
                return True
    return False

def _item_traces_to_text(item_name: str, catalog_item: Optional[Dict[str, Any]], input_text: str) -> bool:
    """Check if the item traces to a word in the input text through name or aliases."""
    text_lower = input_text.lower()
    text_tokens = re.findall(r'[a-zA-Z0-9]+', text_lower)
    
    candidates = [item_name.lower()]
    if catalog_item:
        candidates.append(catalog_item["name"].lower())
        for a in catalog_item.get("aliases", []):
            candidates.append(a.lower())
            
    for cand in candidates:
        cand_tokens = re.findall(r'[a-zA-Z0-9]+', cand)
        for ctok in cand_tokens:
            if len(ctok) <= 2:
                continue
            for ttok in text_tokens:
                if ctok == ttok or (len(ctok) > 3 and (ctok in ttok or ttok in ctok)):
                    return True
                if SequenceMatcher(None, ctok, ttok).ratio() >= 0.75:
                    return True
    return False

def validate_extraction(
    extracted: ExtractorOutput,
    items_catalog: List[Dict[str, Any]],
    customers_catalog: List[Dict[str, Any]],
    raw_text: Optional[str] = None,
) -> Tuple[List[DraftLine], List[DraftIssue], int, int, int, int, bool]:
    """
    ValidatorAgent: receives extractor output and executes catalog, grounding,
    and arithmetic validation strictly in plain Python.
    
    Returns:
    (draft_lines, issues, list_price, discount, effective_total, due, can_save)
    """
    issues: List[DraftIssue] = []
    draft_lines: List[DraftLine] = []
    
    # Fast catalog lookups
    items_by_id = {str(i["_id"]): i for i in items_catalog}
    customers_by_id = {str(c["_id"]): c for c in customers_catalog}

    # 1. Customer check
    customer_name_for_grounding = None
    if not extracted.customerName and not extracted.matchedCustomerId:
        issues.append(DraftIssue(
            field="customer",
            code="MISSING_CUSTOMER",
            message="No customer was identified. Please select or add a customer.",
            severity="error"
        ))
    elif extracted.matchedCustomerId and extracted.matchedCustomerId not in customers_by_id:
        issues.append(DraftIssue(
            field="customer",
            code="UNKNOWN_CUSTOMER_ID",
            message=f"Customer ID was not found in shop records.",
            severity="warning"
        ))
    else:
        # Determine customer name for grounding
        if extracted.matchedCustomerId and extracted.matchedCustomerId in customers_by_id:
            customer_name_for_grounding = customers_by_id[extracted.matchedCustomerId]["name"]
        elif extracted.customerName:
            customer_name_for_grounding = extracted.customerName

    # Grounding Check 1: Customer fuzzy-match in input text
    if raw_text and customer_name_for_grounding:
        # Also check customer aliases if matched
        matched_c = customers_by_id.get(extracted.matchedCustomerId) if extracted.matchedCustomerId else None
        names_to_check = [customer_name_for_grounding]
        if matched_c:
            names_to_check.extend(matched_c.get("aliases", []))
        if not any(_fuzzy_word_in_text(n, raw_text) for n in names_to_check):
            issues.append(DraftIssue(
                field="customer",
                code="CUSTOMER_NOT_IN_TEXT",
                message=f"Customer '{customer_name_for_grounding}' does not trace to any word in the dictated text.",
                severity="error"
            ))

    # 2. Line items check
    if not extracted.lines:
        issues.append(DraftIssue(
            field="lines",
            code="NO_ITEMS",
            message="No line items detected in speech. Add at least one item.",
            severity="error"
        ))

    computed_total = 0

    for idx, line in enumerate(extracted.lines):
        item_name = line.itemName
        matched_id = line.matchedItemId
        qty = line.qty
        unit_price = line.unitPrice
        is_assumed = False

        # Quantity check
        if qty is None or qty <= 0:
            issues.append(DraftIssue(
                field=f"lines[{idx}].qty",
                code="MISSING_QUANTITY",
                message=f"Missing or invalid quantity for item '{item_name}'.",
                severity="error"
            ))
            qty = 1  # default for draft UI

        # Price check & catalog fallback
        catalog_item = items_by_id.get(matched_id) if matched_id else None
        if not catalog_item:
            norm_name = item_name.lower().strip()
            for it in items_catalog:
                if it["name"].lower() == norm_name or norm_name in [a.lower() for a in it.get("aliases", [])]:
                    catalog_item = it
                    matched_id = str(it["_id"])
                    break

        # Grounding Check 2: ITEM_NOT_IN_TEXT (blocking)
        if raw_text and not _item_traces_to_text(item_name, catalog_item, raw_text):
            issues.append(DraftIssue(
                field=f"lines[{idx}].name",
                code="ITEM_NOT_IN_TEXT",
                message=f"Item '{item_name}' does not trace to any word or alias in the input speech.",
                severity="error"
            ))

        # Grounding Check 3: PRICE_OFF_CATALOG (warning)
        # Unit price more than 50% away from the catalog price
        if catalog_item and unit_price is not None:
            cat_price = catalog_item.get("price", 0)
            if cat_price > 0:
                diff = abs(unit_price - cat_price)
                if (diff / cat_price) > 0.50:
                    issues.append(DraftIssue(
                        field=f"lines[{idx}].unitPrice",
                        code="PRICE_OFF_CATALOG",
                        message=f"Unit price ₹{unit_price} is more than 50% away from catalog price ₹{cat_price}.",
                        severity="warning"
                    ))

        # Grounding Check 4: QTY_MISMATCH (warning)
        # A quantity word appears right before an item mention but returned qty differs
        if raw_text and qty is not None:
            # Look for item words in raw_text and examine the preceding word
            tokens = re.findall(r'[a-zA-Z0-9]+', raw_text.lower())
            item_search_tokens = set(re.findall(r'[a-zA-Z0-9]+', item_name.lower()))
            if catalog_item:
                item_search_tokens.update(re.findall(r'[a-zA-Z0-9]+', catalog_item["name"].lower()))
                for a in catalog_item.get("aliases", []):
                    item_search_tokens.update(re.findall(r'[a-zA-Z0-9]+', a.lower()))
            item_search_tokens = {t for t in item_search_tokens if len(t) > 2}

            for t_idx, tok in enumerate(tokens):
                if tok in item_search_tokens and t_idx > 0:
                    prev_word = tokens[t_idx - 1]
                    # Also check two words before e.g. "do silk tie" -> prev_word is "silk", two before is "do"
                    qty_word = None
                    if prev_word in QTY_WORDS_MAP:
                        qty_word = prev_word
                    elif t_idx > 1 and tokens[t_idx - 2] in QTY_WORDS_MAP and prev_word in {"cotton", "silk", "leather", "formal", "casual", "white", "half", "coat"}:
                        qty_word = tokens[t_idx - 2]
                    
                    if qty_word:
                        expected_q = QTY_WORDS_MAP[qty_word]
                        if expected_q != qty:
                            issues.append(DraftIssue(
                                field=f"lines[{idx}].qty",
                                code="QTY_MISMATCH",
                                message=f"Quantity word '{qty_word}' ({expected_q}) appears before item, but extracted qty is {qty}.",
                                severity="warning"
                            ))
                            break


        if unit_price is None:
            if catalog_item:
                unit_price = catalog_item["price"]
                is_assumed = True
                issues.append(DraftIssue(
                    field=f"lines[{idx}].unitPrice",
                    code="ASSUMED_PRICE",
                    message=f"Price for '{item_name}' was not stated. Filled from catalog as ₹{unit_price}.",
                    severity="warning"
                ))
            else:
                unit_price = 0
                issues.append(DraftIssue(
                    field=f"lines[{idx}].unitPrice",
                    code="MISSING_PRICE",
                    message=f"Price for '{item_name}' is missing and not found in catalog.",
                    severity="error"
                ))
        
        # Stock warning check
        if catalog_item and qty is not None:
            if catalog_item.get("stock", 0) < qty:
                issues.append(DraftIssue(
                    field=f"lines[{idx}].stock",
                    code="LOW_STOCK",
                    message=f"Warning: Only {catalog_item.get('stock', 0)} in stock for '{catalog_item['name']}' (selling {qty}).",
                    severity="warning"
                ))

        line_total = compute_line_total(qty, unit_price)
        computed_total += line_total

        draft_lines.append(DraftLine(
            itemId=matched_id,
            name=catalog_item["name"] if catalog_item else item_name,
            qty=qty,
            unitPrice=unit_price,
            lineTotal=line_total,
            isAssumedPrice=is_assumed
        ))

    # 3. Arithmetic & Total Policy:
    # Rule: when a stated total exists, it is the total.
    # Show computed sum of lines as "list price" and difference as "discount".
    # Add a soft warning if discount exceeds 25% of list price.
    list_price = computed_total
    if extracted.statedTotal is not None:
        effective_total = extracted.statedTotal
        discount = list_price - effective_total
        if discount > 0 and list_price > 0:
            discount_pct = (discount / list_price) * 100
            if discount_pct > 25.0:
                issues.append(DraftIssue(
                    field="total",
                    code="HIGH_DISCOUNT",
                    message=f"Discount is ₹{discount} ({round(discount_pct, 1)}% of list price ₹{list_price}). High discount applied.",
                    severity="warning"
                ))
        elif discount < 0:
            # Surcharge / stated total is higher than list price
            surcharge = -discount
            issues.append(DraftIssue(
                field="total",
                code="STATED_TOTAL_ABOVE_LIST",
                message=f"Stated bill (₹{effective_total}) is higher than list price (₹{list_price}) by ₹{surcharge}.",
                severity="warning"
            ))
    else:
        effective_total = list_price
        discount = 0

    paid = extracted.paid if extracted.paid is not None else 0
    if paid < 0:
        paid = 0

    # Paid greater than total check
    if paid > effective_total and effective_total > 0:
        issues.append(DraftIssue(
            field="paid",
            code="PAID_EXCEEDS_TOTAL",
            message=f"Paid amount (₹{paid}) is greater than total bill (₹{effective_total}). Customer will have an advance credit.",
            severity="warning"
        ))

    due = effective_total - paid

    # canSave is false if any issue has severity "error"
    can_save = not any(issue.severity == "error" for issue in issues)

    return draft_lines, issues, list_price, discount, effective_total, due, can_save
