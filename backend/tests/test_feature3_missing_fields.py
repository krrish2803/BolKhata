import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.agents.correction import apply_patch_plan, PatchPlan
from app.schemas import PatchOperation, ExtractorOutput, ExtractedLine
from app.agents.validator import validate_extraction

@pytest.mark.asyncio
async def test_feature3_missing_field_prompt_patch():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        res = await client.post("/api/session")
        assert res.status_code == 200
        workspace_id = res.json()["workspaceId"]
        cookies = res.cookies

        # 1. Parse text with missing customer and missing quantity
        # Text: "do shirt aur trouser diye" -> has items, but no customer name
        parse_res = await client.post(
            "/api/parse",
            json={"text": "do shirt aur trouser diye, 1000 bill"},
            cookies=cookies,
        )
        assert parse_res.status_code == 200
        draft = parse_res.json()
        draft_id = draft["draftId"]

        # Expect blocking issue for missing customer
        issue_codes = [iss["code"] for iss in draft["issues"]]
        assert "MISSING_CUSTOMER" in issue_codes or "CUSTOMER_NOT_IN_TEXT" in issue_codes

        # Get seeded customers to find a customerId
        cust_res = await client.get("/api/customers", cookies=cookies)
        customers = cust_res.json()
        assert len(customers) > 0
        sharma = next((c for c in customers if "sharma" in c["name"].lower()), customers[0])

        # 2. Tap customer chip: apply patch with NO MODEL CALL via /api/drafts/{id}/patch
        patch_res = await client.post(
            f"/api/drafts/{draft_id}/patch",
            json={"operations": [{"op": "set_customer", "customerId": sharma["id"]}]},
            cookies=cookies,
        )
        assert patch_res.status_code == 200
        updated_data = patch_res.json()
        updated_draft = updated_data["draft"]
        assert updated_draft["customer"]["id"] == sharma["id"]
        assert updated_draft["customer"]["name"] == sharma["name"]

        # 3. Tap quantity stepper chip for line 1 (trouser): set_line_qty
        patch_res2 = await client.post(
            f"/api/drafts/{draft_id}/patch",
            json={"operations": [{"op": "set_line_qty", "lineIndex": 1, "qty": 3}]},
            cookies=cookies,
        )
        assert patch_res2.status_code == 200
        updated_draft2 = patch_res2.json()["draft"]
        assert updated_draft2["lines"][1]["qty"] == 3

        # 4. Tap catalog item chip: add_line
        item_res = await client.get("/api/items", cookies=cookies)
        items = item_res.json()
        jeans = next((i for i in items if "jeans" in i["name"].lower()), items[0])
        initial_line_count = len(updated_draft2["lines"])

        patch_res3 = await client.post(
            f"/api/drafts/{draft_id}/patch",
            json={"operations": [{"op": "add_line", "itemId": jeans["id"], "qty": 1}]},
            cookies=cookies,
        )
        assert patch_res3.status_code == 200
        updated_draft3 = patch_res3.json()["draft"]
        assert len(updated_draft3["lines"]) == initial_line_count + 1
        assert any(l["name"] == jeans["name"] for l in updated_draft3["lines"])
