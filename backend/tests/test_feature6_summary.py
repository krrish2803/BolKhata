import pytest
from datetime import datetime, timezone
import pytz
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.agents.summary import get_kolkata_today_range, compute_daily_summary

def test_kolkata_timezone_boundaries():
    # 19 Oct 2026 12:00 UTC is 19 Oct 2026 17:30 IST (Asia/Kolkata)
    test_dt = datetime(2026, 10, 19, 12, 0, 0, tzinfo=timezone.utc)
    utc_start, utc_end, date_str = get_kolkata_today_range(test_dt)

    assert date_str == "19 Oct 2026"
    # Asia/Kolkata is UTC+5:30.
    # 00:00:00 IST is 18:30:00 UTC previous day (18 Oct)
    tz = pytz.timezone("Asia/Kolkata")
    ist_start = utc_start.astimezone(tz)
    ist_end = utc_end.astimezone(tz)

    assert ist_start.hour == 0
    assert ist_start.minute == 0
    assert ist_end.hour == 23
    assert ist_end.minute == 59

def test_compute_daily_summary_empty():
    res = compute_daily_summary([], "19 Oct 2026")
    assert res["entriesCount"] == 0
    assert res["totalSales"] == 0
    assert res["cashCollected"] == 0
    assert res["totalUdhaarGiven"] == 0
    assert "nahi hui hai" in res["narrative"]

def test_compute_daily_summary_integer_math():
    mock_entries = [
        {
            "customerName": "Sharma ji",
            "lines": [{"name": "Shirt", "qty": 2, "unitPrice": 450, "lineTotal": 900}],
            "total": 900,
            "paid": 500,
            "due": 400,
        },
        {
            "customerName": "Verma ji",
            "lines": [{"name": "Trouser", "qty": 1, "unitPrice": 800, "lineTotal": 800}],
            "total": 800,
            "paid": 800,
            "due": 0,
        },
    ]

    res = compute_daily_summary(mock_entries, "19 Oct 2026")
    assert res["entriesCount"] == 2
    assert res["totalSales"] == 1700
    assert res["cashCollected"] == 1300
    assert res["totalUdhaarGiven"] == 400
    assert res["topCustomer"] == "Sharma ji"
    assert "1,700" in res["narrative"]
    assert "1,300" in res["narrative"]
    assert "400" in res["narrative"]

@pytest.mark.asyncio
async def test_today_summary_endpoint_e2e():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        res = await client.post("/api/session")
        assert res.status_code == 200
        cookies = res.cookies

        # Fetch today summary
        sum_res = await client.get("/api/summary/today", cookies=cookies)
        assert sum_res.status_code == 200
        data = sum_res.json()
        assert "date" in data
        assert "entriesCount" in data
        assert "totalSales" in data
        assert "cashCollected" in data
        assert "totalUdhaarGiven" in data
        assert "narrative" in data
        assert isinstance(data["totalSales"], int)
        assert isinstance(data["cashCollected"], int)
        assert isinstance(data["totalUdhaarGiven"], int)
