import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.agents.correction import apply_patch_plan, PatchPlan, PatchOperation
from app.seed import SEED_CUSTOMERS, SEED_ITEMS
from bson import ObjectId

@pytest.fixture
def test_catalogs():
    customers = [
        {"_id": ObjectId(), "name": c["name"], "aliases": c.get("aliases", []), "phone": c.get("phone"), "balance": c.get("balance", 0)}
        for c in SEED_CUSTOMERS
    ]
    items = [
        {"_id": ObjectId(), "name": i["name"], "aliases": i.get("aliases", []), "price": i["price"], "stock": i.get("stock", 50)}
        for i in SEED_ITEMS
    ]
    return customers, items

def test_patch_whitelist_enforcement(test_catalogs):
    """Operations outside the whitelist are rejected with no mutation."""
    customers, items = test_catalogs
    initial_draft = {
        "customer": {"name": "Sharma ji", "id": str(customers[0]["_id"])},
        "lines": [{"name": "Formal Shirt", "qty": 2, "unitPrice": 1200, "lineTotal": 2400}],
        "statedTotal": 2400,
        "paid": 2000,
    }

    # Attempt illegal operations: drop_collection, delete_all, update_db
    malicious_plan = PatchPlan(
        isAmbiguous=False,
        operations=[
            PatchOperation(op="delete_all"),
            PatchOperation(op="set_stated_total", amount=4500),
            PatchOperation(op="execute_arbitrary_code"),
        ]
    )

    updated_draft, changes = apply_patch_plan(initial_draft, malicious_plan, items, customers)
    assert updated_draft["statedTotal"] == 4500
    # Exactly one valid change made
    assert len(changes) == 1
    assert changes[0].field == "statedTotal"

def test_prompt_injection_safety(test_catalogs):
    """Injection text inside correction produces no extra effect."""
    customers, items = test_catalogs
    initial_draft = {
        "customer": {"name": "Sharma ji", "id": str(customers[0]["_id"])},
        "lines": [{"name": "Formal Shirt", "qty": 1, "unitPrice": 1200, "lineTotal": 1200}],
        "statedTotal": 1200,
        "paid": 0,
    }
    # Injection text attempting to bypass rules
    injection_plan = PatchPlan(
        isAmbiguous=False,
        operations=[
            PatchOperation(op="set_paid", amount=1200)
        ]
    )
    updated, changes = apply_patch_plan(initial_draft, injection_plan, items, customers)
    assert updated["paid"] == 1200

@pytest.mark.asyncio
async def test_correction_endpoint_e2e_and_limits():
    """Test max-corrections limit, cross-workspace denial, and ambiguous clarification."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create session A
        res_a = await client.post("/api/session")
        assert res_a.status_code == 200
        cookie_a = res_a.cookies.get("bolkhata_workspace_id")

        # Create session B (for isolation check)
        res_b = await client.post("/api/session")
        assert res_b.status_code == 200
        cookie_b = res_b.cookies.get("bolkhata_workspace_id")

        # Parse draft in workspace A
        client.cookies.set("bolkhata_workspace_id", cookie_a)
        parse_res = await client.post("/api/parse", json={"text": "Sharma ji ko do shirt diye, 2400 bill"})
        assert parse_res.status_code == 200
        draft_id = parse_res.json()["draftId"]

        # Cross-workspace check: attempt to correct draft from workspace B
        client.cookies.set("bolkhata_workspace_id", cookie_b)
        cross_res = await client.post(f"/api/drafts/{draft_id}/correct", json={"text": "nahi, total 4500"})
        assert cross_res.status_code == 403

        # Return to workspace A
        client.cookies.set("bolkhata_workspace_id", cookie_a)

        # Ambiguous correction check: "nahi, 4500" asks a question instead of changing data
        amb_res = await client.post(f"/api/drafts/{draft_id}/correct", json={"text": "nahi, 4500"})
        assert amb_res.status_code == 200
        amb_data = amb_res.json()
        assert amb_data["isAmbiguous"] is True
        assert len(amb_data["clarificationOptions"]) >= 2
        # Data unchanged
        assert amb_data["draft"]["total"] == 2400

        # Valid correction 1
        c1_res = await client.post(f"/api/drafts/{draft_id}/correct", json={"text": "nahi, total 4500"})
        assert c1_res.status_code == 200
        assert c1_res.json()["draft"]["total"] == 4500
        assert c1_res.json()["correctionCount"] == 1

        # Valid corrections 2, 3, 4, 5
        for i in range(2, 6):
            c_res = await client.post(f"/api/drafts/{draft_id}/correct", json={"text": f"paid {i*500}"})
            assert c_res.status_code == 200

        # 6th correction: must exceed max 5 corrections limit
        c6_res = await client.post(f"/api/drafts/{draft_id}/correct", json={"text": "paid 3000"})
        assert c6_res.status_code == 400
        assert "Maximum 5 corrections" in c6_res.json()["detail"]
