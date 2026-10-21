import pytest
from pydantic import ValidationError
from app.schemas import ParseRequest, EditLineInput, CustomerEditInput, EntryCreateRequest

def test_parse_request_valid():
    req = ParseRequest(text="Sharma ji ko do shirt diye 2400 bill 1000 cash")
    assert req.text == "Sharma ji ko do shirt diye 2400 bill 1000 cash"

def test_parse_request_oversized_rejected():
    with pytest.raises(ValidationError):
        ParseRequest(text="a" * 501)

def test_nosql_operator_injection_sanitization():
    # Customer name attempting NoSQL injection string or control chars
    c = CustomerEditInput(name="Sharma ji {\"$gt\": \"\"}", phone="9876543210")
    assert "Sharma ji" in c.name
    assert c.phone == "9876543210"

def test_edit_line_input_negative_rejected():
    with pytest.raises(ValidationError):
        EditLineInput(name="Shirt", qty=-1, unitPrice=1200)
    with pytest.raises(ValidationError):
        EditLineInput(name="Shirt", qty=2, unitPrice=-100)

def test_edit_line_input_bounds():
    with pytest.raises(ValidationError):
        EditLineInput(name="Shirt", qty=1001, unitPrice=1200) # qty > 1000 rejected
