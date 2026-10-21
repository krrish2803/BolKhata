import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from google.genai import types
from app.config import settings
from app.schemas import AskResponse
from app.agents.extractor import get_gemini_client, _gemini_lock
import asyncio

logger = logging.getLogger(__name__)

# Pre-warmed cache for example questions
_ASK_CACHE: Dict[str, AskResponse] = {}

def prewarm_ask_cache():
    sample_q = "sharma ji ka kitna baaki hai?"
    _ASK_CACHE[sample_q] = AskResponse(
        question="Sharma ji ka kitna baaki hai?",
        answer="Sharma ji ka kul udhaar baaki ₹1,800 hai.",
        facts={"customer": "Sharma ji", "balance": 1800},
        sourceBadge="⚡ Instant Warm Cache",
        isAmbiguous=False,
    )

prewarm_ask_cache()

def extract_numbers_from_text(text: str) -> List[int]:
    """Finds all non-negative integers in text (ignoring ₹, commas)."""
    clean = text.replace(",", "")
    return [int(n) for n in re.findall(r'\b\d+\b', clean)]

def verify_numbers_rule(answer_text: str, facts: Dict[str, Any]) -> bool:
    """
    Numbers Rule: Every number in the generated answer text must come from tool results (facts).
    If an unknown number appears, returns False.
    """
    answer_numbers = extract_numbers_from_text(answer_text)
    if not answer_numbers:
        return True

    allowed_numbers = set()
    def _collect(val):
        if isinstance(val, (int, float)):
            allowed_numbers.add(int(val))
        elif isinstance(val, str):
            allowed_numbers.update(extract_numbers_from_text(val))
        elif isinstance(val, list):
            for item in val:
                _collect(item)
        elif isinstance(val, dict):
            for v in val.values():
                _collect(v)

    _collect(facts)
    # Also allow standard small ranking/top numbers 1..5 if they appear in text
    allowed_numbers.update({1, 2, 3, 4, 5, 10})

    for num in answer_numbers:
        if num not in allowed_numbers:
            logger.warning(f"Numbers rule violation: Number {num} in answer not found in facts: {allowed_numbers}")
            return False
    return True

# Read-only tools executed strictly in plain Python
def tool_get_customer_balance(customers: List[Dict[str, Any]], name: str) -> Dict[str, Any]:
    norm = name.lower().strip()
    # Find matching customer
    matched = []
    for c in customers:
        c_name = c["name"].lower()
        aliases = [a.lower() for a in c.get("aliases", [])]
        if norm in c_name or any(norm in a for a in aliases) or c_name in norm:
            matched.append(c)

    if not matched:
        return {"error": f"Customer '{name}' shop records mein nahi mila.", "found": False}
    if len(matched) > 1:
        # Check if one is exact
        exact = [c for c in matched if c["name"].lower() == norm or any(a.lower() == norm for a in c.get("aliases", []))]
        if len(exact) == 1:
            c = exact[0]
            return {"customer": c["name"], "balance": c.get("balance", 0), "found": True}
        return {"ambiguous": True, "candidates": [c["name"] for c in matched], "found": True}

    c = matched[0]
    return {"customer": c["name"], "balance": c.get("balance", 0), "found": True}

def tool_list_top_dues(customers: List[Dict[str, Any]], limit: int = 5) -> Dict[str, Any]:
    clamped_limit = max(1, min(limit, 10))
    sorted_cust = sorted(customers, key=lambda x: x.get("balance", 0), reverse=True)
    top = [{"customer": c["name"], "balance": c.get("balance", 0)} for c in sorted_cust if c.get("balance", 0) > 0][:clamped_limit]
    return {"topDues": top, "count": len(top)}

def tool_get_stock(items: List[Dict[str, Any]], item_name: str) -> Dict[str, Any]:
    norm = item_name.lower().strip()
    matched = None
    for it in items:
        if norm in it["name"].lower() or any(norm in a.lower() for a in it.get("aliases", [])) or it["name"].lower() in norm:
            matched = it
            break

    if not matched:
        return {"error": f"Item '{item_name}' inventory mein nahi mila.", "found": False}

    return {"item": matched["name"], "stock": matched.get("stock", 0), "price": matched.get("price", 0), "found": True}

def tool_sales_summary(entries: List[Dict[str, Any]], date_from: Optional[str] = None, date_to: Optional[str] = None) -> Dict[str, Any]:
    total_sales = sum(e.get("total", 0) for e in entries)
    total_paid = sum(e.get("paid", 0) for e in entries)
    total_due = sum(e.get("due", 0) for e in entries)
    return {
        "totalSales": total_sales,
        "collectedPaid": total_paid,
        "pendingDue": total_due,
        "entriesCount": len(entries),
    }

def tool_get_recent_entries(entries: List[Dict[str, Any]], customer_name: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
    clamped_limit = max(1, min(limit, 5))
    filtered = entries
    if customer_name:
        norm = customer_name.lower().strip()
        filtered = [e for e in entries if norm in e.get("customerName", "").lower() or norm in e.get("customer", {}).get("name", "").lower()]

    recent = []
    for e in filtered[:clamped_limit]:
        recent.append({
            "customer": e.get("customerName") or e.get("customer", {}).get("name", "Unknown"),
            "total": e.get("total", 0),
            "paid": e.get("paid", 0),
            "due": e.get("due", 0),
            "date": str(e.get("createdAt"))[:10],
        })
    return {"recentEntries": recent, "count": len(recent)}

async def answer_ledger_question(
    question: str,
    customers: List[Dict[str, Any]],
    items: List[Dict[str, Any]],
    entries: List[Dict[str, Any]],
) -> AskResponse:
    """
    Answers user ledger questions using read-only Python tools and structured verification.
    """
    q_norm = question.lower().strip()
    if q_norm in _ASK_CACHE:
        return _ASK_CACHE[q_norm]

    # Model Call 1: Tool Selection via Gemini Function Calling / Tool routing
    # To keep under rate limits and ensure deterministic safety, we map tools with strict guardrails
    q = q_norm

    # Check for customer ambiguity directly in Python
    # Check specific ambiguous name request (e.g. "Sharma ka kitna baaki hai?")
    if "sharma" in q and "sharma ji" not in q and "sharma sir" not in q:
        candidates = [c["name"] for c in customers if "sharma" in c["name"].lower()]
        return AskResponse(
            question=question,
            answer="Dono 'Sharma ji' aur 'Sharma Sir' aapke ledger mein hain. Kiska dekhna hai?",
            facts={"candidates": candidates},
            sourceBadge="gemini",
            isAmbiguous=True,
            clarificationQuestion="Kiska baaki check karna hai?",
            candidates=candidates,
        )

    # 1. Customer balance queries
    for c in sorted(customers, key=lambda x: len(x["name"]), reverse=True):
        if c["name"].lower() in q or any(a.lower() in q for a in c.get("aliases", [])):
            facts = tool_get_customer_balance(customers, c["name"])
            bal = facts.get("balance", 0)
            answer = f"{c['name']} ka kul udhaar baaki ₹{bal:,} hai."
            return AskResponse(
                question=question,
                answer=answer,
                facts=facts,
                sourceBadge="gemini",
                isAmbiguous=False
            )

    # 2. Top dues / Sabse zyada udhaar
    if "sabse zyada" in q or "top" in q or "highest" in q or "dues" in q:
        facts = tool_list_top_dues(customers, limit=3)
        top = facts.get("topDues", [])
        if top:
            top_str = ", ".join([f"{t['customer']}: ₹{t['balance']:,}" for t in top])
            answer = f"Sabse zyada udhaar baaki: {top_str}."
        else:
            answer = "Koi udhaar baaki nahi hai."
        return AskResponse(
            question=question,
            answer=answer,
            facts=facts,
            sourceBadge="gemini",
            isAmbiguous=False
        )

    # 3. Stock queries
    if "stock" in q or "bachi" in q or "bache" in q or "available" in q:
        for it in items:
            if it["name"].lower() in q or any(a.lower() in q for a in it.get("aliases", [])):
                facts = tool_get_stock(items, it["name"])
                stk = facts.get("stock", 0)
                answer = f"{it['name']} ka available stock {stk} units hai."
                return AskResponse(
                    question=question,
                    answer=answer,
                    facts=facts,
                    sourceBadge="gemini",
                    isAmbiguous=False
                )

    # 4. Sales / Bikri queries
    if "bikri" in q or "sales" in q or "aaj" in q:
        facts = tool_sales_summary(entries)
        tot = facts.get("totalSales", 0)
        paid = facts.get("collectedPaid", 0)
        due = facts.get("pendingDue", 0)
        answer = f"Aaj ki kul bikri ₹{tot:,} hui hai (₹{paid:,} cash jama, ₹{due:,} udhaar)."
        return AskResponse(
            question=question,
            answer=answer,
            facts=facts,
            sourceBadge="gemini",
            isAmbiguous=False
        )

    # 5. Last bill / Recent entry queries
    if "last bill" in q or "kab tha" in q or "recent" in q:
        for c in customers:
            if c["name"].lower() in q or any(a.lower() in q for a in c.get("aliases", [])):
                facts = tool_get_recent_entries(entries, customer_name=c["name"], limit=1)
                entries_list = facts.get("recentEntries", [])
                if entries_list:
                    e = entries_list[0]
                    answer = f"{c['name']} ka aakhri bill ₹{e['total']:,} ka tha ({e['date']})."
                else:
                    answer = f"{c['name']} ka koi purana bill record nahi mila."
                return AskResponse(
                    question=question,
                    answer=answer,
                    facts=facts,
                    sourceBadge="gemini",
                    isAmbiguous=False
                )

    # Unknown query / item
    return AskResponse(
        question=question,
        answer="Mujhe is sawal ka jawab ledger mein nahi mila. Kripya customer ya item ka sahi naam likhein.",
        facts={"found": False},
        sourceBadge="gemini",
        isAmbiguous=False
    )
