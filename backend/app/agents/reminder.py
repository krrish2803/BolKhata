import urllib.parse
from typing import Optional, Dict, Any
from app.config import settings

def build_reminder_message(
    customer_name: str,
    due_amount: int,
    last_entry_date: Optional[str] = None,
    tone: str = "polite",
) -> str:
    """
    Feature 5: Overdue payment reminder templates in plain Python (no model call by default).
    Tones supported: 'polite' | 'firm'
    """
    date_str = f" (pichhla hisaab: {last_entry_date})" if last_entry_date else ""

    if tone == "firm":
        text = (
            f"Namaste {customer_name} ji,\n\n"
            f"Aapke bahi-khata mein ₹{due_amount} ka baaki udhaar kafi samay se bacha hua hai{date_str}. "
            f"Kripya karke is rashi ka bhugtan jald se jald kar dijiye taaki hisaab clear ho sake.\n\n"
            f"Shop contact / UPI: +91 9874961805\n"
            f"Dhanyawaad,\nBolKhata Store"
        )
    else:  # polite default
        text = (
            f"Namaste {customer_name} ji,\n\n"
            f"Umeed hai aap kushal-mangal hain. Aapke account mein kul ₹{due_amount} ka hisaab baaki hai{date_str}. "
            f"Jab bhi samay mile, kripya ise clear kar dijiyega.\n\n"
            f"Koi sawaal ho toh bataiye: +91 9874961805\n"
            f"Dhanyawaad,\nBolKhata Store"
        )
    return text

def build_wa_reminder_url(phone: Optional[str], text: str) -> str:
    """
    Format wa.me URL using only digits for phone, URL-encoded text.
    """
    encoded = urllib.parse.quote(text)
    clean_phone = "".join(c for c in (phone or "") if c.isdigit())
    if clean_phone:
        return f"https://wa.me/{clean_phone}?text={encoded}"
    return f"https://wa.me/?text={encoded}"
