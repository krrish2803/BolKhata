from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator
import re

# Strict input models with security sanitization

def sanitize_safe_text(val: str, max_len: int = 500) -> str:
    if not isinstance(val, str):
        raise ValueError("Must be a string")
    # Disallow control characters except newline and tab
    val = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', val)
    val = val.strip()
    if len(val) > max_len:
        raise ValueError(f"Exceeds maximum character length of {max_len}")
    return val

class ParseRequest(BaseModel):
    text: str = Field(..., max_length=500, description="Hinglish/Hindi/English dictated sale text")

    @field_validator("text")
    def validate_text(cls, v: str) -> str:
        return sanitize_safe_text(v, max_len=500)

class ExtractedLine(BaseModel):
    itemName: str
    matchedItemId: Optional[str] = None
    qty: Optional[int] = Field(None, ge=1, le=1000)
    unitPrice: Optional[int] = Field(None, ge=0, le=1000000)

class ExtractorOutput(BaseModel):
    customerName: Optional[str] = None
    matchedCustomerId: Optional[str] = None
    lines: List[ExtractedLine] = Field(default_factory=list, max_length=20)
    statedTotal: Optional[int] = Field(None, ge=0, le=1000000)
    paid: Optional[int] = Field(None, ge=0, le=1000000)
    notes: Optional[str] = None

class DraftIssue(BaseModel):
    field: str
    code: str
    message: str
    severity: str = "warning" # "error" | "warning"

class DraftLine(BaseModel):
    itemId: Optional[str] = None
    name: str
    qty: int = Field(..., ge=1, le=1000)
    unitPrice: int = Field(..., ge=0, le=1000000)
    lineTotal: int = Field(..., ge=0, le=1000000)
    isAssumedPrice: bool = False

class DraftResponse(BaseModel):
    draftId: str
    rawText: str
    customer: Optional[dict] = None # { id, name, isNew }
    lines: List[DraftLine] = Field(default_factory=list)
    statedTotal: Optional[int] = None
    computedTotal: int = 0
    listPrice: int = 0
    discount: int = 0
    total: int = 0
    paid: int = 0
    due: int = 0
    issues: List[DraftIssue] = Field(default_factory=list)
    canSave: bool = True
    modelInfo: Optional[dict] = None

class EditLineInput(BaseModel):
    itemId: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    qty: int = Field(..., ge=1, le=1000)
    unitPrice: int = Field(..., ge=0, le=1000000)

    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        return sanitize_safe_text(v, max_len=100)

class CustomerEditInput(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    isNew: bool = False
    phone: Optional[str] = None

    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        return sanitize_safe_text(v, max_len=100)

    @field_validator("phone")
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        clean = re.sub(r'\D', '', v)
        if len(clean) > 15:
            raise ValueError("Invalid phone number length")
        return clean

class EntryCreateRequest(BaseModel):
    draftId: str = Field(..., min_length=1, max_length=64)
    customer: Optional[CustomerEditInput] = None
    lines: Optional[List[EditLineInput]] = None
    paid: Optional[int] = Field(None, ge=0, le=1000000)
    # Any client-sent total/due will be ignored by the backend
    total: Optional[int] = None
    due: Optional[int] = None

class EntryResponse(BaseModel):
    id: str
    workspaceId: str
    customerId: str
    customerName: str
    lines: List[dict]
    total: int
    paid: int
    due: int
    rawText: str
    createdAt: str
    customerUpdatedBalance: int
    waReceiptUrl: str

# --- Phase 2 Schemas ---

class CorrectionRequest(BaseModel):
    text: str = Field(..., max_length=300, description="Voice/text correction follow-up")

    @field_validator("text")
    def validate_text(cls, v: str) -> str:
        return sanitize_safe_text(v, max_len=300)

class PatchOperation(BaseModel):
    op: str = Field(..., description="Whitelisted operation type")
    # set_customer: customerId OR (name with new customer)
    customerId: Optional[str] = None
    customerName: Optional[str] = None
    # set_line_qty / set_line_item / set_line_price / remove_line
    lineIndex: Optional[int] = Field(None, ge=0, le=50)
    qty: Optional[int] = Field(None, ge=1, le=1000)
    itemId: Optional[str] = None
    unitPrice: Optional[int] = Field(None, ge=0, le=1000000)
    # set_stated_total / set_paid
    amount: Optional[int] = Field(None, ge=0, le=1000000)

class PatchPlan(BaseModel):
    isAmbiguous: bool = False
    ambiguityQuestion: Optional[str] = None
    clarificationOptions: List[str] = Field(default_factory=list)
    operations: List[PatchOperation] = Field(default_factory=list)

class ChangeDiff(BaseModel):
    field: str
    before: Any
    after: Any

class CorrectionResponse(BaseModel):
    draft: DraftResponse
    changes: List[ChangeDiff] = Field(default_factory=list)
    isAmbiguous: bool = False
    clarificationQuestion: Optional[str] = None
    clarificationOptions: List[str] = Field(default_factory=list)
    correctionCount: int = 0

class PatchApplyRequest(BaseModel):
    operations: List[PatchOperation] = Field(..., description="Direct patch operations to apply without calling model")

class AskRequest(BaseModel):
    question: str = Field(..., max_length=300, description="Ledger query in Hinglish/English")

    @field_validator("question")
    def validate_question(cls, v: str) -> str:
        return sanitize_safe_text(v, max_len=300)

class AskResponse(BaseModel):
    question: str
    answer: str
    facts: Dict[str, Any] = Field(default_factory=dict)
    sourceBadge: Optional[str] = "gemini"
    isAmbiguous: bool = False
    clarificationQuestion: Optional[str] = None
    candidates: List[str] = Field(default_factory=list)

class FuzzyMatchRequest(BaseModel):
    name: str = Field(..., max_length=100)

class CandidateCustomer(BaseModel):
    id: str
    name: str
    phone: Optional[str] = None
    balance: int = 0
    aliases: List[str] = Field(default_factory=list)

class FuzzyMatchResponse(BaseModel):
    decision: str  # "AUTO_MATCH" | "ASK_USER" | "NEW_CUSTOMER"
    score: float
    customer: Optional[CandidateCustomer] = None
    candidates: List[CandidateCustomer] = Field(default_factory=list)
    nearDuplicateWarning: Optional[str] = None

class AddAliasRequest(BaseModel):
    alias: str = Field(..., max_length=100)

class ReminderResponse(BaseModel):
    customerName: str
    balance: int
    tone: str
    text: str
    waUrl: str

class DailySummaryResponse(BaseModel):
    date: str
    entriesCount: int
    totalSales: int
    cashCollected: int
    totalUdhaarGiven: int
    topCustomer: Optional[str] = None
    topItem: Optional[str] = None
    narrative: str

class UndoEntryResponse(BaseModel):
    status: str
    undoneEntryId: str
    customerName: str
    reversedDue: int
    customerNewBalance: int
    restoredLines: List[Dict[str, Any]]
    message: str

class UpdateCustomerPhoneRequest(BaseModel):
    phone: str = Field(..., max_length=20)

class AuthRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20)
    shopName: str = Field(..., min_length=1, max_length=100)
    shopType: str = Field(default="Kirana / General Store", max_length=100)
    pin: str = Field(..., min_length=4, max_length=4)

    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        return sanitize_safe_text(v, max_len=100)

    @field_validator("shopName")
    def validate_shop(cls, v: str) -> str:
        return sanitize_safe_text(v, max_len=100)

    @field_validator("phone")
    def validate_phone(cls, v: str) -> str:
        clean = re.sub(r'\D', '', v)
        if len(clean) < 10 or len(clean) > 15:
            raise ValueError("Phone number must have between 10 and 15 digits")
        return clean

class AuthLoginRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=20)
    pin: str = Field(..., min_length=4, max_length=4)

    @field_validator("phone")
    def validate_phone(cls, v: str) -> str:
        clean = re.sub(r'\D', '', v)
        if len(clean) < 10 or len(clean) > 15:
            raise ValueError("Phone number must have between 10 and 15 digits")
        return clean

class AuthUserResponse(BaseModel):
    id: str
    name: str
    whatsAppNumber: str
    shopName: str
    shopType: str
    workspaceId: str
    isDemo: bool = False







