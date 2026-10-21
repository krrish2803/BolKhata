import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.agents.reminder import build_reminder_message, build_wa_reminder_url

def test_reminder_templates_polite_and_firm():
    # Polite tone
    polite = build_reminder_message(
        customer_name="Sharma ji",
        due_amount=2200,
        last_entry_date="15 Oct 2026",
        tone="polite"
    )
    assert "Sharma ji" in polite
    assert "₹2200" in polite
    assert "15 Oct 2026" in polite
    assert "kushal-mangal" in polite

    # Firm tone
    firm = build_reminder_message(
        customer_name="Verma ji",
        due_amount=5000,
        last_entry_date="10 Oct 2026",
        tone="firm"
    )
    assert "Verma ji" in firm
    assert "₹5000" in firm
    assert "jald se jald" in firm

def test_wa_reminder_url_formatting():
    # Phone digits only
    url = build_wa_reminder_url("+91 98765-43210", "Hello Sharma ji")
    assert url.startswith("https://wa.me/919876543210?text=")
    assert "Hello%20Sharma%20ji" in url

    # No phone provided
    url_no_phone = build_wa_reminder_url(None, "Hello")
    assert url_no_phone == "https://wa.me/?text=Hello"

@pytest.mark.asyncio
async def test_reminder_endpoint_e2e():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        res = await client.post("/api/session")
        assert res.status_code == 200
        cookies = res.cookies

        # Get seeded customers
        c_res = await client.get("/api/customers", cookies=cookies)
        assert c_res.status_code == 200
        customers = c_res.json()
        assert len(customers) > 0

        # Find customer with udhaar balance
        cust = next((c for c in customers if c["balance"] > 0), customers[0])

        # Test GET /api/customers/{id}/reminder?tone=polite
        rem_res = await client.get(f"/api/customers/{cust['id']}/reminder?tone=polite", cookies=cookies)
        assert rem_res.status_code == 200
        data = rem_res.json()
        assert data["customerName"] == cust["name"]
        assert data["balance"] == cust["balance"]
        assert data["tone"] == "polite"
        assert f"₹{cust['balance']}" in data["text"]
        assert "waUrl" in data
        assert data["waUrl"].startswith("https://wa.me/")

        # Test GET /api/customers/{id}/reminder?tone=firm
        rem_firm = await client.get(f"/api/customers/{cust['id']}/reminder?tone=firm", cookies=cookies)
        assert rem_firm.status_code == 200
        data_firm = rem_firm.json()
        assert data_firm["tone"] == "firm"
        assert "jald se jald" in data_firm["text"]
