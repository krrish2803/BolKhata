import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from app.main import app
from app.db import get_db
from app.cache import set_cached_extraction, get_cached_extraction
from app.schemas import ExtractorOutput, ExtractedLine

@pytest.mark.asyncio
async def test_item1_tampered_payload_cannot_change_balance_beyond_recomputed_due():
    """
    POST /api/entries:
    Ignore client-sent total, paid and due. Load the draft, recompute lineTotal,
    total and due from the lines in Python, validate paid (0 <= paid, bounded),
    and use only the recomputed values for the entry and the balance update.
    Test: a tampered payload cannot change balance beyond the recomputed due.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a workspace
        session_res = await client.post("/api/session")
        assert session_res.status_code == 200

        # Parse a draft: 2 items @ 1200 = 2400. Paid = 1000. True due = 1400.
        parse_res = await client.post("/api/parse", json={
            "text": "Sharma ji ko do shirt 2400 me di, 1000 cash mila baaki udhaar"
        })
        assert parse_res.status_code == 200
        draft_id = parse_res.json()["draftId"]

        # Tampered entry save request: client maliciously sends total=10, paid=10, due=0
        save_res = await client.post("/api/entries", json={
            "draftId": draft_id,
            "customer": {"name": "Sharma ji", "isNew": False},
            "lines": [{"name": "Formal Shirt", "qty": 2, "unitPrice": 1200}],
            "total": 10,   # TAMPERED
            "paid": 1000,
            "due": 0       # TAMPERED: trying to avoid udhaar
        })
        assert save_res.status_code == 200
        entry = save_res.json()

        # The server must have ignored tampered total and due:
        assert entry["total"] == 2400
        assert entry["paid"] == 1000
        assert entry["due"] == 1400

        # Customer's original balance in seed data is 1800.
        # Updated balance must be exactly 1800 + 1400 = 3200 (NOT 1800 + 0)
        assert entry["customerUpdatedBalance"] == 3200

@pytest.mark.asyncio
async def test_item1_saving_same_draft_twice_creates_exactly_one_entry():
    """
    Test: saving the same draft twice creates exactly one entry (idempotency).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/session")
        parse_res = await client.post("/api/parse", json={
            "text": "Verma ji ko ek trouser 1800 me diya, poora udhaar"
        })
        assert parse_res.status_code == 200
        draft_id = parse_res.json()["draftId"]

        payload = {
            "draftId": draft_id,
            "customer": {"name": "Verma ji", "isNew": False},
            "lines": [{"name": "Trouser", "qty": 1, "unitPrice": 1800}],
            "paid": 0
        }

        # First save
        res1 = await client.post("/api/entries", json=payload)
        assert res1.status_code == 200
        entry_id1 = res1.json()["id"]

        # Second save with exact same draftId
        res2 = await client.post("/api/entries", json=payload)
        assert res2.status_code == 200
        entry_id2 = res2.json()["id"]

        # Must return the same entry ID
        assert entry_id1 == entry_id2

        # Check total entries in ledger
        ledger_res = await client.get("/api/ledger")
        entries = ledger_res.json()
        matching_entries = [e for e in entries if e["id"] == entry_id1]
        assert len(matching_entries) == 1

@pytest.mark.asyncio
async def test_item2_undo_entry_by_id_and_idempotency():
    """
    POST /api/entries/{entryId}/undo:
    Reject unless the entry is the most recent non-undone entry in the workspace and is within 15 minutes.
    Mark it status="undone" with undoneAt instead of deleting.
    Make it idempotent, so a repeated call returns the same result and never touches another entry.
    Test: two rapid undo calls reverse exactly one entry.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/session")

        # Create entry 1
        p1 = await client.post("/api/parse", json={"text": "Sharma ji ko ek shirt 1200 me di"})
        e1 = await client.post("/api/entries", json={
            "draftId": p1.json()["draftId"],
            "customer": {"name": "Sharma ji", "isNew": False},
            "lines": [{"name": "Formal Shirt", "qty": 1, "unitPrice": 1200}],
            "paid": 0
        })
        assert e1.status_code == 200
        entry1_id = e1.json()["id"]

        # Create entry 2
        p2 = await client.post("/api/parse", json={"text": "Verma ji ko ek trouser 1800 me di"})
        e2 = await client.post("/api/entries", json={
            "draftId": p2.json()["draftId"],
            "customer": {"name": "Verma ji", "isNew": False},
            "lines": [{"name": "Trouser", "qty": 1, "unitPrice": 1800}],
            "paid": 0
        })
        assert e2.status_code == 200
        entry2_id = e2.json()["id"]

        # Try to undo Entry 1 while Entry 2 is the most recent active entry -> must be rejected
        bad_undo = await client.post(f"/api/entries/{entry1_id}/undo")
        assert bad_undo.status_code == 400
        assert "most recent active entry" in bad_undo.json()["detail"]

        # First undo call on Entry 2 (most recent) -> SUCCESS
        undo1 = await client.post(f"/api/entries/{entry2_id}/undo")
        assert undo1.status_code == 200
        assert undo1.json()["status"] == "undone"

        # Rapid second undo call on Entry 2 -> IDEMPOTENT (returns same result, does NOT touch Entry 1)
        undo2 = await client.post(f"/api/entries/{entry2_id}/undo")
        assert undo2.status_code == 200
        assert undo2.json()["status"] == "undone"
        assert undo2.json()["undoneEntryId"] == entry2_id

        # Verify entry2 is marked status="undone" with undoneAt
        db = get_db()
        entry2_doc = await db.entries.find_one({"_id": ObjectId(entry2_id)})
        assert entry2_doc["status"] == "undone"
        assert "undoneAt" in entry2_doc

        # Entry 1 was untouched and is still active
        entry1_doc = await db.entries.find_one({"_id": ObjectId(entry1_id)})
        assert entry1_doc["status"] == "active"

@pytest.mark.asyncio
async def test_item3_demo_reset_forbidden_for_real_accounts():
    """
    /api/demo/reset: only allowed when the current workspace has isDemo=true, otherwise 403.
    Test with a real account.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register real account (isDemo=False)
        reg = await client.post("/api/auth/register", json={
            "name": "Kailash Chand",
            "phone": "9812300099",
            "shopName": "Chand Cloth Emporium",
            "shopType": "Clothing & Garments",
            "pin": "7832"
        })
        assert reg.status_code == 200

        # Attempt /api/demo/reset with real account session -> MUST RETURN 403 Forbidden
        reset_res = await client.post("/api/demo/reset")
        assert reset_res.status_code == 403
        assert "only allowed for demo workspaces" in reset_res.json()["detail"]

        # In contrast, create a demo workspace -> MUST SUCCEED
        await client.post("/api/session")
        demo_reset = await client.post("/api/demo/reset")
        assert demo_reset.status_code == 200
        assert demo_reset.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_item4_cache_never_leaks_ids_across_workspaces():
    """
    Cache: make sure cached extractor output contains no customer or item ids
    and no workspace-specific data. Match ids after the cache lookup.
    Test: workspace B never receives ids from workspace A through the cache.
    """
    workspace_a_id = "ws_aaa_111"
    workspace_b_id = "ws_bbb_222"

    text = "Sharma ji ko do shirt 2400 me di"

    # Simulate an extractor output with workspace A specific IDs
    output_a = ExtractorOutput(
        customerName="Sharma ji",
        matchedCustomerId="cust_id_from_workspace_a",
        lines=[
            ExtractedLine(
                itemName="Formal Shirt",
                matchedItemId="item_id_from_workspace_a",
                qty=2,
                unitPrice=1200
            )
        ],
        statedTotal=2400,
        paid=0
    )
    model_info = {"source": "gemini", "model": "gemini-2.5-flash"}

    # Store in cache
    set_cached_extraction(text, output_a, model_info)

    # Retrieve from cache as if workspace B was looking it up
    retrieved, info = get_cached_extraction(text)
    assert retrieved is not None

    # The cached extraction MUST HAVE STRIPPED ALL IDs
    assert retrieved.matchedCustomerId is None
    for line in retrieved.lines:
        assert line.matchedItemId is None

@pytest.mark.asyncio
async def test_item6_generic_workspace_mutation_rate_limit():
    """
    Add a generic per-workspace rate limit on all mutating endpoints.
    """
    from app.config import settings
    import app.routes as routes
    routes._WORKSPACE_MUTATION_TRACKER.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/session")

        # Rapidly call a mutating endpoint up to rate limit
        # Temporarily lower limit to test easily
        original_limit = settings.WORKSPACE_MUTATION_RPM
        try:
            settings.WORKSPACE_MUTATION_RPM = 3
            # 3 mutations succeed
            for _ in range(3):
                res = await client.post("/api/ask", json={"question": "total sales?"})
                assert res.status_code == 200

            # 4th mutation must be rejected with 429
            res4 = await client.post("/api/ask", json={"question": "total sales?"})
            assert res4.status_code == 429
            assert "Rate limit exceeded" in res4.json()["detail"]
        finally:
            settings.WORKSPACE_MUTATION_RPM = original_limit

@pytest.mark.asyncio
async def test_item7_csrf_origin_mismatch_rejected():
    """
    Check the Origin header on all state-changing requests and reject mismatches.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/session")

        # Mutating request with unauthorized cross-site Origin
        res = await client.post(
            "/api/parse",
            json={"text": "Sharma ji ko ek shirt di"},
            headers={"Origin": "https://malicious-phishing-site.com"}
        )
        assert res.status_code == 403
        assert "Origin mismatch" in res.json()["detail"]
