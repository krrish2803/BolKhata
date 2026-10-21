from datetime import datetime, timezone
import pytz
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict

def get_kolkata_today_range(now_utc: Optional[datetime] = None) -> Tuple[datetime, datetime, str]:
    """
    Computes start of day (00:00:00) and end of day (23:59:59.999999) in Asia/Kolkata,
    returned as UTC-aware datetime objects for querying MongoDB, plus formatted date string.
    """
    tz = pytz.timezone("Asia/Kolkata")
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    elif now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    # Convert to Kolkata local time
    kolkata_now = now_utc.astimezone(tz)
    kolkata_start = kolkata_now.replace(hour=0, minute=0, second=0, microsecond=0)
    kolkata_end = kolkata_now.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Convert back to UTC for standard database matching
    utc_start = kolkata_start.astimezone(timezone.utc)
    utc_end = kolkata_end.astimezone(timezone.utc)
    date_str = kolkata_now.strftime("%d %b %Y")

    return utc_start, utc_end, date_str

def compute_daily_summary(entries: List[Dict[str, Any]], date_str: str) -> Dict[str, Any]:
    """
    Computes daily summary stats strictly in plain Python integer rupees.
    Returns:
    {
      "date": str,
      "entriesCount": int,
      "totalSales": int,
      "cashCollected": int,
      "totalUdhaarGiven": int,
      "topCustomer": Optional[str],
      "topItem": Optional[str],
      "narrative": str
    }
    """
    entries_count = len(entries)
    if entries_count == 0:
        return {
            "date": date_str,
            "entriesCount": 0,
            "totalSales": 0,
            "cashCollected": 0,
            "totalUdhaarGiven": 0,
            "topCustomer": None,
            "topItem": None,
            "narrative": f"Aaj ({date_str}) abhi tak koi bikri darj nahi hui hai."
        }

    total_sales = 0
    cash_collected = 0
    total_udhaar = 0
    customer_spend = defaultdict(int)
    item_qty_count = defaultdict(int)

    for e in entries:
        tot = int(e.get("total", 0))
        pd = int(e.get("paid", 0))
        du = int(e.get("due", 0))

        total_sales += tot
        cash_collected += pd
        total_udhaar += du

        cust_name = e.get("customerName") or "Customer"
        customer_spend[cust_name] += tot

        for line in e.get("lines", []):
            item_name = line.get("name") or "Item"
            qty = int(line.get("qty", 1))
            item_qty_count[item_name] += qty

    top_customer = max(customer_spend.items(), key=lambda x: x[1])[0] if customer_spend else None
    top_item = max(item_qty_count.items(), key=lambda x: x[1])[0] if item_qty_count else None

    # Compose short natural Hinglish narrative
    narrative_parts = [
        f"Aaj kul ₹{total_sales:,} ki bikri hui",
        f"jisme se ₹{cash_collected:,} cash mila",
        f"aur ₹{total_udhaar:,} udhaar raha."
    ]
    narrative = f"{narrative_parts[0]}, {narrative_parts[1]} {narrative_parts[2]}"
    if top_customer:
        narrative += f" Sabse zyada bikri {top_customer} ko hui."

    return {
        "date": date_str,
        "entriesCount": entries_count,
        "totalSales": total_sales,
        "cashCollected": cash_collected,
        "totalUdhaarGiven": total_udhaar,
        "topCustomer": top_customer,
        "topItem": top_item,
        "narrative": narrative
    }
