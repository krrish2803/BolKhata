import pytest
from app.accounting import (
    compute_line_total,
    compute_entry_totals,
    update_customer_balance,
    decrement_stock,
)

def test_compute_line_total():
    assert compute_line_total(2, 1200) == 2400
    assert compute_line_total(1, 1800) == 1800
    assert compute_line_total(0, 500) == 0

def test_compute_line_total_negative_raises():
    with pytest.raises(ValueError):
        compute_line_total(-1, 1200)
    with pytest.raises(ValueError):
        compute_line_total(2, -500)

def test_compute_entry_totals_standard():
    lines = [
        {"qty": 2, "unitPrice": 1200},
        {"qty": 1, "unitPrice": 1800},
    ]
    total, due = compute_entry_totals(lines, paid=2000)
    assert total == 4200
    assert due == 2200

def test_compute_entry_totals_full_cash():
    lines = [{"qty": 1, "unitPrice": 1450}]
    total, due = compute_entry_totals(lines, paid=1450)
    assert total == 1450
    assert due == 0

def test_compute_entry_totals_advance_payment():
    lines = [{"qty": 1, "unitPrice": 800}]
    total, due = compute_entry_totals(lines, paid=1000)
    assert total == 800
    assert due == -200  # Customer has 200 advance credit

def test_update_customer_balance_adds_udhaar():
    # Previous udhaar was 1800, added 2200 due -> 4000
    new_bal = update_customer_balance(1800, 2200)
    assert new_bal == 4000
    assert isinstance(new_bal, int)

def test_update_customer_balance_reduces_on_advance():
    # Previous balance 1000, customer pays 1200 for 1000 bill (due = -200) -> 800
    new_bal = update_customer_balance(1000, -200)
    assert new_bal == 800

def test_decrement_stock():
    assert decrement_stock(45, 2) == 43
    assert decrement_stock(10, 10) == 0
    assert decrement_stock(5, 7) == -2  # Exact integer subtraction allowed with warning
