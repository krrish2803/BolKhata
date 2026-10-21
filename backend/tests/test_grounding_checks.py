import pytest
from bson import ObjectId
from app.seed import SEED_CUSTOMERS, SEED_ITEMS
from app.agents.validator import validate_extraction
from app.schemas import ExtractorOutput, ExtractedLine

@pytest.fixture
def catalogs():
    customers_catalog = [
        {"_id": ObjectId(), "name": c["name"], "aliases": c.get("aliases", []), "phone": c.get("phone"), "balance": c.get("balance", 0)}
        for c in SEED_CUSTOMERS
    ]
    items_catalog = [
        {"_id": ObjectId(), "name": i["name"], "aliases": i.get("aliases", []), "price": i["price"], "stock": i.get("stock", 50)}
        for i in SEED_ITEMS
    ]
    return customers_catalog, items_catalog

def test_nvidia_failure_fixture_1_customer_not_in_text(catalogs):
    """
    NVIDIA Failure 1 (Case #2):
    Speech text: 'Sharma Sir ko ek coat blazer aur do silk tie diya, poora cash 5400'
    Model hallucinated customer: 'Chopra Saab'
    Check: Must flag CUSTOMER_NOT_IN_TEXT (blocking).
    """
    customers_catalog, items_catalog = catalogs
    raw_text = "Sharma Sir ko ek coat blazer aur do silk tie diya, poora cash 5400"
    
    # Hallucinated output from NVIDIA
    extracted = ExtractorOutput(
        customerName="Chopra Saab",
        matchedCustomerId=None,
        lines=[
            ExtractedLine(itemName="Casual Blazer", qty=1, unitPrice=4500),
            ExtractedLine(itemName="Silk Tie", qty=2, unitPrice=450),
        ],
        statedTotal=5400,
        paid=5400,
    )
    
    draft_lines, issues, list_p, disc, total, due, can_save = validate_extraction(
        extracted, items_catalog, customers_catalog, raw_text=raw_text
    )
    
    issue_codes = [i.code for i in issues]
    assert "CUSTOMER_NOT_IN_TEXT" in issue_codes
    assert can_save is False

def test_nvidia_failure_fixture_2_price_off_catalog(catalogs):
    """
    NVIDIA Failure 2 (Case #5):
    Speech text: 'Khan bhai ne char shirt liya, pachis sau bill, poora cash'
    Catalog price for Formal Shirt is 1200.
    Model output: unitPrice = 2500 (diff > 50% from 1200).
    Check: Must flag PRICE_OFF_CATALOG (warning).
    """
    customers_catalog, items_catalog = catalogs
    raw_text = "Khan bhai ne char shirt liya, pachis sau bill, poora cash"
    
    extracted = ExtractorOutput(
        customerName="Khan Bhai",
        matchedCustomerId=None,
        lines=[
            ExtractedLine(itemName="Formal Shirt", qty=4, unitPrice=2500),
        ],
        statedTotal=10000,
        paid=10000,
    )
    
    draft_lines, issues, list_p, disc, total, due, can_save = validate_extraction(
        extracted, items_catalog, customers_catalog, raw_text=raw_text
    )
    
    issue_codes = [i.code for i in issues]
    assert "PRICE_OFF_CATALOG" in issue_codes

def test_nvidia_failure_fixture_3_item_not_in_text(catalogs):
    """
    NVIDIA Failure 3 (Case #6):
    Speech text: 'Gupta ji ko do belt aur char moja diya, total 1780, ek rupaye nahi diya poora baaki'
    Items in text: belt (Leather Belt) and moja (Cotton Socks).
    Model hallucinated: 'Silk Tie' and 'Linen Handkerchief'
    Check: Must flag ITEM_NOT_IN_TEXT (blocking).
    """
    customers_catalog, items_catalog = catalogs
    raw_text = "Gupta ji ko do belt aur char moja diya, total 1780, ek rupaye nahi diya poora baaki"
    
    extracted = ExtractorOutput(
        customerName="Gupta Hardware",
        matchedCustomerId=None,
        lines=[
            ExtractedLine(itemName="Silk Tie", qty=2, unitPrice=650),
            ExtractedLine(itemName="Linen Handkerchief", qty=4, unitPrice=120),
        ],
        statedTotal=1780,
        paid=0,
    )
    
    draft_lines, issues, list_p, disc, total, due, can_save = validate_extraction(
        extracted, items_catalog, customers_catalog, raw_text=raw_text
    )
    
    issue_codes = [i.code for i in issues]
    assert "ITEM_NOT_IN_TEXT" in issue_codes
    assert can_save is False

def test_nvidia_failure_fixture_4_item_not_in_text_leather_belt(catalogs):
    """
    NVIDIA Failure 4 (Case #11):
    Speech text: 'Khan saab ne do kurta aur ek pajama liya, 3800 bill, poora udhaar'
    Model hallucinated: 'Leather Belt'
    Check: Must flag ITEM_NOT_IN_TEXT.
    """
    customers_catalog, items_catalog = catalogs
    raw_text = "Khan saab ne do kurta aur ek pajama liya, 3800 bill, poora udhaar"
    
    extracted = ExtractorOutput(
        customerName="Khan Bhai",
        matchedCustomerId=None,
        lines=[
            ExtractedLine(itemName="Linen Pajama", qty=2, unitPrice=800),
            ExtractedLine(itemName="Leather Belt", qty=1, unitPrice=650),
        ],
        statedTotal=3800,
        paid=0,
    )
    
    draft_lines, issues, list_p, disc, total, due, can_save = validate_extraction(
        extracted, items_catalog, customers_catalog, raw_text=raw_text
    )
    
    issue_codes = [i.code for i in issues]
    assert "ITEM_NOT_IN_TEXT" in issue_codes

def test_nvidia_failure_fixture_5_qty_mismatch(catalogs):
    """
    NVIDIA Failure 5 (Case #13):
    Speech text: 'Mishraji ne chhe underwear vest liya, 1500 bill, 1500 poora cash'
    Quantity word 'chhe' (6) is right before 'underwear vest', but model extracted qty=1 and unitPrice=1500.
    Check: Must flag QTY_MISMATCH (warning) and PRICE_OFF_CATALOG.
    """
    customers_catalog, items_catalog = catalogs
    raw_text = "Mishraji ne chhe underwear vest liya, 1500 bill, 1500 poora cash"
    
    extracted = ExtractorOutput(
        customerName="Mishra Cloth",
        matchedCustomerId=None,
        lines=[
            ExtractedLine(itemName="Innerwear Vest", qty=1, unitPrice=1500),
        ],
        statedTotal=1500,
        paid=1500,
    )
    
    draft_lines, issues, list_p, disc, total, due, can_save = validate_extraction(
        extracted, items_catalog, customers_catalog, raw_text=raw_text
    )
    
    issue_codes = [i.code for i in issues]
    assert "QTY_MISMATCH" in issue_codes
    assert "PRICE_OFF_CATALOG" in issue_codes

def test_nvidia_failure_fixture_6_item_not_in_text(catalogs):
    """
    NVIDIA Failure 6 (Case #14):
    Speech text: 'Patel ji ko do leather belt aur do shirt diye, total 3700, 2000 diya baaki udhaar'
    Model output: 'Silk Tie' (qty 2) instead of 'Leather Belt'.
    Check: Must flag ITEM_NOT_IN_TEXT.
    """
    customers_catalog, items_catalog = catalogs
    raw_text = "Patel ji ko do leather belt aur do shirt diye, total 3700, 2000 diya baaki udhaar"
    
    extracted = ExtractorOutput(
        customerName="Patel Tailor",
        matchedCustomerId=None,
        lines=[
            ExtractedLine(itemName="Silk Tie", qty=2, unitPrice=450),
            ExtractedLine(itemName="Formal Shirt", qty=2, unitPrice=1200),
        ],
        statedTotal=3700,
        paid=2000,
    )
    
    draft_lines, issues, list_p, disc, total, due, can_save = validate_extraction(
        extracted, items_catalog, customers_catalog, raw_text=raw_text
    )
    
    issue_codes = [i.code for i in issues]
    assert "ITEM_NOT_IN_TEXT" in issue_codes

def test_nvidia_failure_fixture_7_qty_mismatch(catalogs):
    """
    NVIDIA Failure 7 (Case #17):
    Speech text: 'Vermaji ne char pant trouser liya, total 7200, 5000 diya baaki udhar'
    Quantity word 'char' (4) is right before 'pant trouser', but model extracted qty=3.
    Check: Must flag QTY_MISMATCH.
    """
    customers_catalog, items_catalog = catalogs
    raw_text = "Vermaji ne char pant trouser liya, total 7200, 5000 diya baaki udhar"
    
    extracted = ExtractorOutput(
        customerName="Verma ji",
        matchedCustomerId=None,
        lines=[
            ExtractedLine(itemName="Trouser", qty=3, unitPrice=2400),
        ],
        statedTotal=7200,
        paid=5000,
    )
    
    draft_lines, issues, list_p, disc, total, due, can_save = validate_extraction(
        extracted, items_catalog, customers_catalog, raw_text=raw_text
    )
    
    issue_codes = [i.code for i in issues]
    assert "QTY_MISMATCH" in issue_codes

def test_nvidia_failure_fixture_8_item_not_in_text(catalogs):
    """
    NVIDIA Failure 8 (Case #18):
    Speech text: 'Khan bhai ko das socks moja aur do rumaal diya, total 1320, 1000 abhi diya'
    Model hallucinated: 'Cotton Shorts' (which is not in text).
    Check: Must flag ITEM_NOT_IN_TEXT.
    """
    customers_catalog, items_catalog = catalogs
    raw_text = "Khan bhai ko das socks moja aur do rumaal diya, total 1320, 1000 abhi diya"
    
    extracted = ExtractorOutput(
        customerName="Khan Bhai",
        matchedCustomerId=None,
        lines=[
            ExtractedLine(itemName="Linen Handkerchief", qty=11, unitPrice=120),
            ExtractedLine(itemName="Cotton Shorts", qty=2, unitPrice=60),
        ],
        statedTotal=1320,
        paid=1000,
    )
    
    draft_lines, issues, list_p, disc, total, due, can_save = validate_extraction(
        extracted, items_catalog, customers_catalog, raw_text=raw_text
    )
    
    issue_codes = [i.code for i in issues]
    assert "ITEM_NOT_IN_TEXT" in issue_codes
