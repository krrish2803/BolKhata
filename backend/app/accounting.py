from typing import List, Tuple, Dict, Any

def compute_line_total(qty: int, unit_price: int) -> int:
    """Integer rupees calculation: qty * unit_price"""
    if qty < 0 or unit_price < 0:
        raise ValueError("Quantities and prices must be non-negative integers")
    return int(qty * unit_price)

def compute_entry_totals(lines: List[Dict[str, Any]], paid: int) -> Tuple[int, int]:
    """
    Computes (total, due) strictly in integer rupees.
    due = total - paid
    """
    if paid < 0:
        raise ValueError("Paid amount cannot be negative")
    
    total = 0
    for line in lines:
        qty = int(line.get("qty", 0))
        unit_price = int(line.get("unitPrice", 0))
        total += compute_line_total(qty, unit_price)
    
    due = total - paid
    return total, due

def update_customer_balance(current_balance: int, due: int) -> int:
    """
    Balance rule: Customer balance is positive when the customer owes the shop.
    Adding 'due' (which is positive when udhaar increases) adds to balance.
    If paid > total (due < 0), balance decreases (or goes negative if customer has advance credit).
    """
    return int(current_balance + due)

def decrement_stock(current_stock: int, qty_sold: int) -> int:
    """
    Updates available inventory stock.
    Stock can go below zero if items were physically sold without prior stock entry,
    but math is always exact integer subtraction.
    """
    return int(current_stock - qty_sold)
