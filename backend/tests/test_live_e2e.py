import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
import json
from app.main import app

@pytest.mark.asyncio
async def test_full_pipeline():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("\n=======================================================")
        print("  BOLKHATA END-TO-END FEATURE TEST RUNNER")
        print("=======================================================\n")

        # 1. Health check
        res = await client.get("/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        print("1. [PASS] Health check OK:", res.json())

        # 2. POST /api/session (Create Workspace + Seed Data)
        res = await client.post("/api/session")
        assert res.status_code == 200, f"Session create failed: {res.text}"
        session_data = res.json()
        cookies = res.cookies
        assert "workspaceId" in session_data
        print(f"2. [PASS] Session & Workspace created: {session_data['workspaceId']} (Cookie set)")

        # 3. GET /api/customers & GET /api/items (Verify Seed Data)
        res_cust = await client.get("/api/customers", cookies=cookies)
        assert res_cust.status_code == 200
        customers = res_cust.json()
        assert len(customers) == 8, f"Expected 8 seeded customers, got {len(customers)}"
        print(f"3. [PASS] Seeded Customers verified: {len(customers)} customers loaded.")

        res_items = await client.get("/api/items", cookies=cookies)
        assert res_items.status_code == 200
        items = res_items.json()
        assert len(items) == 12, f"Expected 12 seeded items, got {len(items)}"
        print(f"4. [PASS] Seeded Menswear Items verified: {len(items)} items loaded.")

        # 4. POST /api/parse (Run Agent Pipeline on Hinglish Text)
        sample_sale = "Sharma ji ko do shirt aur ek trouser diye, 4200 bill, 2000 abhi diya, baaki udhaar"
        res_parse = await client.post("/api/parse", json={"text": sample_sale}, cookies=cookies)
        assert res_parse.status_code == 200, f"Parse failed: {res_parse.text}"
        draft = res_parse.json()
        assert draft["draftId"], "Missing draftId"
        assert draft["customer"]["name"] == "Sharma ji", f"Expected 'Sharma ji', got {draft['customer']['name']}"
        assert len(draft["lines"]) == 2, f"Expected 2 lines, got {len(draft['lines'])}"
        assert draft["total"] == 4200, f"Expected 4200 total, got {draft['total']}"
        assert draft["paid"] == 2000, f"Expected 2000 paid, got {draft['paid']}"
        assert draft["due"] == 2200, f"Expected 2200 due, got {draft['due']}"
        print(f"5. [PASS] Agent Parse Pipeline OK:")
        print(f"   Customer: {draft['customer']['name']} | Total: ₹{draft['total']} | Paid: ₹{draft['paid']} | Due: ₹{draft['due']}")

        # 5. POST /api/entries (Save Entry to Ledger, update balance, decrement stock)
        entry_payload = {
            "draftId": draft["draftId"],
            "customer": {
                "id": draft["customer"]["id"],
                "name": draft["customer"]["name"],
                "isNew": False,
                "phone": "9876543210"
            },
            "lines": draft["lines"],
            "paid": draft["paid"]
        }
        res_entry = await client.post("/api/entries", json=entry_payload, cookies=cookies)
        assert res_entry.status_code == 200, f"Save entry failed: {res_entry.text}"
        entry = res_entry.json()
        assert entry["total"] == 4200
        assert entry["due"] == 2200
        assert "waReceiptUrl" in entry
        print(f"6. [PASS] Save Entry OK: Entry ID {entry['id']}")
        print(f"   Updated Customer Balance: ₹{entry['customerUpdatedBalance']}")
        print(f"   WhatsApp Receipt URL generated: {entry['waReceiptUrl'][:60]}...")

        # 6. Test Idempotency (Saving the same draftId again must not duplicate)
        res_entry_dup = await client.post("/api/entries", json=entry_payload, cookies=cookies)
        assert res_entry_dup.status_code == 200
        entry_dup = res_entry_dup.json()
        assert entry_dup["id"] == entry["id"], "Idempotency failed: generated different entry id"
        print("7. [PASS] Idempotency verified: duplicate save returns original entry without duplicating records.")

        # 7. GET /api/ledger (Verify Entry in History)
        res_ledger = await client.get("/api/ledger", cookies=cookies)
        assert res_ledger.status_code == 200
        ledger = res_ledger.json()
        assert len(ledger) == 1
        assert ledger[0]["customerName"] == "Sharma ji"
        print(f"8. [PASS] Ledger History verified: {len(ledger)} entry recorded.")

        # 8. GET /api/entries/{id}/receipt (Verify receipt endpoint)
        res_receipt = await client.get(f"/api/entries/{entry['id']}/receipt", cookies=cookies)
        assert res_receipt.status_code == 200
        receipt_data = res_receipt.json()
        assert "text" in receipt_data and "waUrl" in receipt_data
        print("9. [PASS] GET /api/entries/{id}/receipt returned valid WhatsApp text & URL.")

        # 9. Verify Stock Decrement
        res_items_after = await client.get("/api/items", cookies=cookies)
        items_after = res_items_after.json()
        shirt_after = next(i for i in items_after if i["name"] == "Formal Shirt")
        # 45 original stock - 2 sold = 43
        assert shirt_after["stock"] == 43, f"Expected 43 stock for Formal Shirt, got {shirt_after['stock']}"
        print(f"10. [PASS] Inventory stock decremented accurately: Formal Shirt stock is now {shirt_after['stock']}.")

        print("\n=======================================================")
        print("  ALL 10 FEATURE TESTS PASSED SUCCESSFULLY! (10/10)")
        print("=======================================================\n")

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
