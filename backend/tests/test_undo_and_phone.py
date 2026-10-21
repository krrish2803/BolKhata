import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timedelta, timezone
from app.main import app
from app.db import get_db

@pytest.mark.asyncio
async def test_undo_last_entry_and_phone_update():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create fresh workspace
        res = await client.post("/api/session")
        assert res.status_code == 200
        cookies = res.cookies
        ws_id = res.json()["workspaceId"]

        # Fetch seeded customer and item
        cust_res = await client.get("/api/customers", cookies=cookies)
        customers = cust_res.json()
        cust = customers[0]
        initial_balance = cust["balance"]

        item_res = await client.get("/api/items", cookies=cookies)
        items = item_res.json()
        item = items[0]
        initial_stock = item["stock"]

        # 2. Record a sale entry
        # Save entry: 2x item, paid 500, due = (2 * item['price']) - 500
        line_total = 2 * item["price"]
        due_amount = line_total - 500
        save_payload = {
            "draftId": "test_draft_undo_1",
            "customer": {
                "id": cust["id"],
                "name": cust["name"],
                "isNew": False,
                "phone": cust.get("phone")
            },
            "lines": [
                {
                    "itemId": item["id"],
                    "name": item["name"],
                    "qty": 2,
                    "unitPrice": item["price"]
                }
            ],
            "paid": 500
        }

        # Mock draft in DB to satisfy idempotency check
        db = get_db()
        await db.drafts.insert_one({
            "_id": "test_draft_undo_1",
            "workspaceId": ws_id,
            "rawText": "test sale for undo",
            "createdAt": datetime.now(timezone.utc)
        })

        entry_res = await client.post("/api/entries", json=save_payload, cookies=cookies)
        assert entry_res.status_code == 200
        created_entry = entry_res.json()
        assert created_entry["due"] == due_amount

        # Check balance increased and stock decreased
        c_after = await client.get("/api/customers", cookies=cookies)
        cust_after = next(c for c in c_after.json() if c["id"] == cust["id"])
        assert cust_after["balance"] == initial_balance + due_amount

        i_after = await client.get("/api/items", cookies=cookies)
        item_after = next(i for i in i_after.json() if i["id"] == item["id"])
        assert item_after["stock"] == initial_stock - 2

        # 3. Undo the entry via POST /api/entries/undo
        undo_res = await client.post("/api/entries/undo", cookies=cookies)
        assert undo_res.status_code == 200
        undo_data = undo_res.json()
        assert undo_data["status"] == "undone"
        assert undo_data["reversedDue"] == due_amount
        assert undo_data["customerNewBalance"] == initial_balance

        # Verify balance and stock strictly reversed in Python
        c_reverted = await client.get("/api/customers", cookies=cookies)
        cust_reverted = next(c for c in c_reverted.json() if c["id"] == cust["id"])
        assert cust_reverted["balance"] == initial_balance

        i_reverted = await client.get("/api/items", cookies=cookies)
        item_reverted = next(i for i in i_reverted.json() if i["id"] == item["id"])
        assert item_reverted["stock"] == initial_stock

        # 4. Idempotency check: Calling undo again immediately returns 404 (entry already undone/deleted)
        undo_again = await client.post("/api/entries/undo", cookies=cookies)
        assert undo_again.status_code == 404

        # 5. Customer Phone Update test: PATCH /api/customers/{id}/phone
        phone_res = await client.patch(
            f"/api/customers/{cust['id']}/phone",
            json={"phone": "9874961805"},
            cookies=cookies
        )
        assert phone_res.status_code == 200
        phone_data = phone_res.json()
        assert "+91 9874961805" in phone_data["phone"]

        # Verify invalid phone format rejection
        bad_phone = await client.patch(
            f"/api/customers/{cust['id']}/phone",
            json={"phone": "123"},
            cookies=cookies
        )
        assert bad_phone.status_code == 400
