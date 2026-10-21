import pytest
from app.agents.fuzzy_customer import match_customer_fuzzy, normalize_name, sanitize_alias, transliterate_devanagari
from app.config import settings

def test_devanagari_transliteration_and_normalization():
    # वर्मा जी -> verma ji
    norm = normalize_name("वर्मा जी")
    assert "verma" in norm
    assert "ji" in norm

    # Punctuation & case stripping
    assert normalize_name("Verma, Ji!!") == "verma ji"
    assert normalize_name("  Sharma   Sir  ") == "sharma sir"

def test_spelling_variants_matching():
    catalog = [
        {"_id": "c1", "name": "Verma ji", "aliases": []},
        {"_id": "c2", "name": "Gupta Enterprises", "aliases": []},
    ]

    # "Vermaji" vs "Verma ji"
    res1 = match_customer_fuzzy("Vermaji", catalog)
    assert res1.decision in ("AUTO_MATCH", "ASK_USER")
    assert res1.candidates[0]["name"] == "Verma ji"

    # Devanagari variant "वर्मा जी"
    res2 = match_customer_fuzzy("वर्मा जी", catalog)
    assert res2.candidates[0]["name"] == "Verma ji"
    assert res2.score >= 80.0

def test_honorifics_preserved_sharma_ji_vs_sharma_sir():
    """
    CRITICAL: Sharma ji and Sharma Sir are different seeded customers.
    If the stripped base names are identical across multiple customers,
    always ask, never auto-match!
    """
    catalog = [
        {"_id": "s1", "name": "Sharma ji", "aliases": []},
        {"_id": "s2", "name": "Sharma Sir", "aliases": []},
    ]

    # Query with generic base "Sharma"
    res_base = match_customer_fuzzy("Sharma", catalog)
    assert res_base.decision == "ASK_USER", "Base name Sharma must ask user, never auto-match"
    candidate_names = [c["name"] for c in res_base.candidates]
    assert "Sharma ji" in candidate_names
    assert "Sharma Sir" in candidate_names

    # Query "Sharma ji" should not auto-match to "Sharma Sir"
    res_ji = match_customer_fuzzy("Sharma ji", catalog)
    assert res_ji.decision == "AUTO_MATCH"
    assert res_ji.customer["name"] == "Sharma ji"

    res_sir = match_customer_fuzzy("Sharma Sir", catalog)
    assert res_sir.decision == "AUTO_MATCH"
    assert res_sir.customer["name"] == "Sharma Sir"

def test_near_duplicate_warning_and_thresholds():
    catalog = [
        {"_id": "c1", "name": "Sharma ji", "aliases": []},
    ]

    # "Sharmaji Cloth" -> high similarity to "Sharma ji", should ask or show near-duplicate warning
    res = match_customer_fuzzy("Sharmaji Store", catalog)
    assert res.score >= 70.0
    assert res.near_duplicate_warning is not None
    assert "Sharma ji" in res.near_duplicate_warning

    # Completely new customer below 70
    res_new = match_customer_fuzzy("Zeeshan Electronics", catalog)
    assert res_new.decision == "NEW_CUSTOMER"
    assert res_new.score < 70.0

def test_alias_learning_cap_and_sanitization():
    # Sanitization
    assert sanitize_alias("  Sharmaji\x00\x1f  ", max_length=40) == "Sharmaji"
    long_alias = "a" * 50
    assert len(sanitize_alias(long_alias, max_length=40)) <= 40

    # Ensure empty string is rejected
    assert sanitize_alias("   ") is None
