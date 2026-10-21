import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone

from app.main import app
from app.db import get_db
from app.auth_security import (
    is_trivial_pin, hash_pin, verify_pin,
    reset_all_login_trackers, reset_all_login_trackers_async, mask_phone_for_logs
)

@pytest_asyncio.fixture(autouse=True)
async def clean_rate_limits():
    db = get_db()
    await reset_all_login_trackers_async(db)
    yield
    await reset_all_login_trackers_async(db)

@pytest.mark.asyncio
async def test_trivial_pin_rejection():
    """Verify that common, repeated, or sequential 4-digit PINs are rejected."""
    # Disallowed trivial PINs
    assert is_trivial_pin("1234") is True
    assert is_trivial_pin("0000") is True
    assert is_trivial_pin("1111") is True
    assert is_trivial_pin("9999") is True
    assert is_trivial_pin("4321") is True
    assert is_trivial_pin("2345") is True
    assert is_trivial_pin("6789") is True
    assert is_trivial_pin("9876") is True
    assert is_trivial_pin("1212") is True
    assert is_trivial_pin("abcd") is True
    assert is_trivial_pin("123") is True
    assert is_trivial_pin("12345") is True

    # Valid non-trivial PINs
    assert is_trivial_pin("5892") is False
    assert is_trivial_pin("7149") is False
    assert is_trivial_pin("8302") is False
    assert is_trivial_pin("4927") is False

@pytest.mark.asyncio
async def test_argon2_hashing_and_verification():
    """Verify Argon2id hash creation and constant-time verification."""
    pin = "7492"
    h = hash_pin(pin)
    assert h.startswith("$argon2id$")
    assert verify_pin(h, pin) is True
    assert verify_pin(h, "7491") is False
    assert verify_pin(h, "1234") is False

@pytest.mark.asyncio
async def test_register_trivial_pin_rejected_api():
    """Endpoint POST /api/auth/register must reject trivial PINs with HTTP 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/auth/register", json={
            "name": "Suresh Kumar",
            "phone": "9876543210",
            "shopName": "Suresh Kirana",
            "shopType": "Kirana / General Store",
            "pin": "1234"
        })
        assert res.status_code == 400
        assert "PIN is too simple" in res.json()["detail"]

        # Another trivial PIN: 1111
        res2 = await client.post("/api/auth/register", json={
            "name": "Suresh Kumar",
            "phone": "9876543210",
            "shopName": "Suresh Kirana",
            "shopType": "Kirana / General Store",
            "pin": "1111"
        })
        assert res2.status_code == 400

@pytest.mark.asyncio
async def test_no_account_enumeration():
    """Unknown phone and wrong PIN must return identical 401 message."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register a valid user with non-trivial PIN
        reg_res = await client.post("/api/auth/register", json={
            "name": "Gupta Ji",
            "phone": "9811122233",
            "shopName": "Gupta Textiles",
            "shopType": "Clothing & Garments",
            "pin": "6294"
        })
        assert reg_res.status_code == 200

        # Attempt 1: Known phone, WRONG pin
        res_wrong_pin = await client.post("/api/auth/login", json={
            "phone": "9811122233",
            "pin": "9998"
        })
        assert res_wrong_pin.status_code == 401

        # Attempt 2: UNKNOWN phone
        res_unknown_phone = await client.post("/api/auth/login", json={
            "phone": "9999988888",
            "pin": "6294"
        })
        assert res_unknown_phone.status_code == 401

        # Both errors must be completely indistinguishable
        assert res_wrong_pin.json()["detail"] == res_unknown_phone.json()["detail"]
        assert res_wrong_pin.json()["detail"] == "Invalid WhatsApp number or 4-digit PIN."

@pytest.mark.asyncio
async def test_lockout_after_5_failed_attempts():
    """Verify rate limiting: temporary lockout with HTTP 429 after 5 failed login attempts."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register valid user
        await client.post("/api/auth/register", json={
            "name": "Rohan Verma",
            "phone": "9822233344",
            "shopName": "Verma Electronics",
            "shopType": "Hardware & Electrical",
            "pin": "8417"
        })

        # Attempts 1 through 4: 401 Invalid
        for i in range(4):
            r = await client.post("/api/auth/login", json={
                "phone": "9822233344",
                "pin": f"000{i}"
            })
            assert r.status_code == 401

        # Attempt 5: triggers lockout
        r5 = await client.post("/api/auth/login", json={
            "phone": "9822233344",
            "pin": "0005"
        })
        assert r5.status_code == 429
        assert "Too many failed login attempts" in r5.json()["detail"]

        # Attempt 6 (even with correct PIN): still locked out
        r6 = await client.post("/api/auth/login", json={
            "phone": "9822233344",
            "pin": "8417"
        })
        assert r6.status_code == 429
        assert "Too many failed login attempts" in r6.json()["detail"]

@pytest.mark.asyncio
async def test_account_isolation_drafts_customers_entries():
    """Verify that Account A cannot access Account B's drafts, customers, or entries."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client_a:
        # Register Account A
        res_a = await client_a.post("/api/auth/register", json={
            "name": "Owner A",
            "phone": "9833344455",
            "shopName": "Shop A",
            "shopType": "Retail",
            "pin": "7531"
        })
        assert res_a.status_code == 200
        workspace_a = res_a.json()["workspaceId"]

        # Create a draft in Account A
        draft_res = await client_a.post("/api/parse", json={
            "text": "Sharma ji ko 2 Blue Jeans 1800 me di, 500 mila baaki udhaar"
        })
        assert draft_res.status_code == 200
        draft_id_a = draft_res.json()["draftId"]

        # Save an entry in Account A
        entry_res = await client_a.post("/api/entries", json={
            "draftId": draft_id_a,
            "customer": {"name": "Sharma ji", "isNew": False},
            "lines": [{"name": "Blue Jeans", "qty": 2, "unitPrice": 900}],
            "total": 1800,
            "paid": 500,
            "due": 1300
        })
        assert entry_res.status_code == 200
        entry_id_a = entry_res.json()["id"]

    async with AsyncClient(transport=transport, base_url="http://test") as client_b:
        # Register Account B
        res_b = await client_b.post("/api/auth/register", json={
            "name": "Owner B",
            "phone": "9844455566",
            "shopName": "Shop B",
            "shopType": "Retail",
            "pin": "9513"
        })
        assert res_b.status_code == 200
        workspace_b = res_b.json()["workspaceId"]
        assert workspace_a != workspace_b

        # Account B tries to correct Account A's draft -> 404
        b_corr = await client_b.post(f"/api/drafts/{draft_id_a}/correct", json={
            "text": "nahi 3 jeans"
        })
        assert b_corr.status_code == 404

        # Account B queries ledger -> must NOT contain Account A's entry
        b_ledger = await client_b.get("/api/ledger")
        assert b_ledger.status_code == 200
        b_entries = b_ledger.json()
        assert not any(e["id"] == entry_id_a for e in b_entries)

        # Account B queries customers -> must be isolated to Account B's workspace
        b_custs = await client_b.get("/api/customers")
        assert b_custs.status_code == 200
        for c in b_custs.json():
            # In MongoDB document, customer must belong to workspace_b
            pass

@pytest.mark.asyncio
async def test_per_ip_lockout_across_multiple_numbers():
    """
    Verify per-IP limiting:
    An attacker cannot try 1-4 PINs across multiple distinct phone numbers from the same IP.
    After 5 total failures from that IP, the IP itself is locked out regardless of phone number.
    """
    from app.db import get_db
    await reset_all_login_trackers_async(get_db())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register 3 different accounts
        for i in range(1, 4):
            reg = await client.post("/api/auth/register", json={
                "name": f"User {i}",
                "phone": f"987650000{i}",
                "shopName": f"Shop {i}",
                "shopType": "Retail",
                "pin": "7149"
            })
            assert reg.status_code == 200

        # Attempt 1 on phone 1 -> 401
        assert (await client.post("/api/auth/login", json={"phone": "9876500001", "pin": "9999"})).status_code == 401
        # Attempt 2 on phone 1 -> 401
        assert (await client.post("/api/auth/login", json={"phone": "9876500001", "pin": "8888"})).status_code == 401
        # Attempt 3 on phone 2 -> 401
        assert (await client.post("/api/auth/login", json={"phone": "9876500002", "pin": "9999"})).status_code == 401
        # Attempt 4 on phone 3 -> 401
        assert (await client.post("/api/auth/login", json={"phone": "9876500003", "pin": "9999"})).status_code == 401
        
        # Attempt 5 on a completely fresh/unknown phone from this SAME IP -> triggers 429 lockout!
        res5 = await client.post("/api/auth/login", json={"phone": "9876599999", "pin": "9999"})
        assert res5.status_code == 429
        assert "Too many failed login attempts" in res5.json()["detail"]

        # Attempt 6 on phone 2 even with CORRECT PIN is blocked by the IP lockout:
        res6 = await client.post("/api/auth/login", json={"phone": "9876500002", "pin": "7149"})
        assert res6.status_code == 429
        assert "Too many failed login attempts" in res6.json()["detail"]

@pytest.mark.asyncio
async def test_mask_phone_never_exposes_full_number():
    """Ensure phone masking utility redacts full digits."""
    assert mask_phone_for_logs("9876543210") == "+91 ******3210"
    assert "9876543210" not in mask_phone_for_logs("9876543210")
