from fastapi import APIRouter, Request, Response, HTTPException, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import urllib.parse
import logging
import time
from bson import ObjectId

from app.db import get_db
from app.config import settings
from app.schemas import (
    ParseRequest, DraftResponse, EntryCreateRequest, EntryResponse,
    CorrectionRequest, CorrectionResponse, PatchApplyRequest, ExtractorOutput, ExtractedLine, DraftLine,
    AskRequest, AskResponse, FuzzyMatchRequest, FuzzyMatchResponse, CandidateCustomer, AddAliasRequest,
    ReminderResponse, DailySummaryResponse, UndoEntryResponse, UpdateCustomerPhoneRequest,
    AuthRegisterRequest, AuthLoginRequest, AuthUserResponse
)
from app.seed import seed_workspace
from app.auth_security import (
    is_trivial_pin, hash_pin, verify_pin, mask_phone_for_logs,
    check_login_rate_limit, record_failed_login, reset_login_attempts
)

logger = logging.getLogger("bolkhata.routes")
from app.agents.pipeline import run_pipeline
from app.agents.validator import validate_extraction
from app.agents.correction import plan_correction, apply_patch_plan, PatchPlan
from app.agents.ask import answer_ledger_question
from app.agents.fuzzy_customer import match_customer_fuzzy, sanitize_alias
from app.agents.reminder import build_reminder_message, build_wa_reminder_url
from app.agents.summary import get_kolkata_today_range, compute_daily_summary
from app.accounting import compute_line_total, compute_entry_totals, update_customer_balance, decrement_stock

router = APIRouter()

COOKIE_NAME = "bolkhata_workspace_id"

# In-memory rate limiting fallbacks
_WORKSPACE_MUTATION_TRACKER: Dict[str, List[float]] = {}
_IP_WORKSPACE_CREATION_TRACKER: Dict[str, List[float]] = {}

def get_client_ip_from_request(request: Request) -> str:
    """Read client IP safely, honoring X-Forwarded-For ONLY from configured trusted proxies."""
    remote_ip = request.client.host if request.client else "127.0.0.1"
    if remote_ip in settings.trusted_proxy_list:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return remote_ip

async def enforce_workspace_mutation_rate_limit(workspace_id: str, db = None):
    """Enforces rate limit for state-changing mutations on a workspace."""
    now = time.time()
    # Check in-memory tracker
    timestamps = _WORKSPACE_MUTATION_TRACKER.get(workspace_id, [])
    # Keep only timestamps in the last 60 seconds
    timestamps = [t for t in timestamps if now - t < 60]
    if len(timestamps) >= settings.WORKSPACE_MUTATION_RPM:
        logger.warning(f"Workspace mutation rate limit exceeded for {workspace_id}")
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Workspace is limited to {settings.WORKSPACE_MUTATION_RPM} mutations per minute."
        )
    timestamps.append(now)
    _WORKSPACE_MUTATION_TRACKER[workspace_id] = timestamps

async def enforce_ip_workspace_creation_limit(client_ip: str, db = None):
    """Enforces per-IP cap on workspace creation."""
    now = time.time()
    timestamps = _IP_WORKSPACE_CREATION_TRACKER.get(client_ip, [])
    # 24 hours window = 86400 seconds
    timestamps = [t for t in timestamps if now - t < 86400]
    if len(timestamps) >= settings.WORKSPACE_CREATION_DAILY_CAP:
        logger.warning(f"IP workspace creation daily cap exceeded for IP {client_ip}")
        raise HTTPException(
            status_code=429,
            detail=f"Daily workspace creation limit exceeded ({settings.WORKSPACE_CREATION_DAILY_CAP} per day per IP)."
        )
    timestamps.append(now)
    _IP_WORKSPACE_CREATION_TRACKER[client_ip] = timestamps

async def get_current_workspace_id(request: Request) -> str:
    """
    Extracts workspaceId from httpOnly cookie.
    Guarantees strict workspace isolation: all queries filter by this workspaceId.
    Enforces per-workspace rate limits on mutating requests (POST, PUT, PATCH, DELETE).
    """
    workspace_id = request.cookies.get(COOKIE_NAME)
    if not workspace_id:
        raise HTTPException(status_code=401, detail="No active workspace session. Please initiate session.")
    
    # Validate format
    if not isinstance(workspace_id, str) or len(workspace_id) > 64:
        raise HTTPException(status_code=400, detail="Invalid workspace session")
    
    db = get_db()
    if db is not None:
        ws = await db.workspaces.find_one({"_id": workspace_id})
        if not ws:
            raise HTTPException(status_code=401, detail="Workspace session expired or not found")

    # Enforce mutation rate limit on mutating HTTP methods
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        await enforce_workspace_mutation_rate_limit(workspace_id, db)
            
    return workspace_id

# 1. POST /api/session (Try the Demo)
@router.post("/session")
async def create_session(request: Request, response: Response):
    """
    Creates a new demo workspace with 24h TTL, seeds fake customers and items,
    and returns { workspaceId } stored in an httpOnly SameSite cookie.
    Allows one-click access for visitors with no phone or PIN required.
    Enforces per-IP daily cap on workspace creations.
    """
    client_ip = get_client_ip_from_request(request)
    db = get_db()
    await enforce_ip_workspace_creation_limit(client_ip, db)

    workspace_id = str(ObjectId())
    now = datetime.utcnow()
    expires_at = now + timedelta(hours=24)

    if db is not None:
        await db.workspaces.insert_one({
            "_id": workspace_id,
            "createdAt": now,
            "expiresAt": expires_at,
            "isDemo": True,
            "createdFromIp": client_ip,
        })
        # Seed fake data
        await seed_workspace(db, workspace_id)

    # Set httpOnly, SameSite cookie
    response.set_cookie(
        key=COOKIE_NAME,
        value=workspace_id,
        httponly=True,
        samesite="lax",
        secure=settings.ENV != "dev",
        max_age=86400, # 24 hours
        path="/"
    )

    return {"workspaceId": workspace_id, "expiresAt": expires_at.isoformat(), "isDemo": True}

# Auth Routes: Register & Login for Real Accounts
@router.post("/auth/register", response_model=AuthUserResponse)
async def auth_register(payload: AuthRegisterRequest, request: Request, response: Response):
    """
    Register a new shopkeeper account.
    - Rejects trivial PINs (1234, 0000, 1111, repeated or sequential digits)
    - Hashes PIN with Argon2id
    - Scopes account to its own dedicated workspace
    - Issues httpOnly SameSite cookie
    - Never logs phone or PIN
    """
    masked_phone = mask_phone_for_logs(payload.phone)
    logger.info(f"Account registration attempt for phone: {masked_phone}")

    # Check trivial PIN
    if is_trivial_pin(payload.pin):
        raise HTTPException(
            status_code=400,
            detail="PIN is too simple. Do not use 1234, repeated, or sequential digits (e.g. 1111, 4321)."
        )

    db = get_db()
    if db is not None:
        existing = await db.users.find_one({"phone": payload.phone})
        if existing:
            # Consistent response to avoid account enumeration
            raise HTTPException(
                status_code=400,
                detail="An account with this WhatsApp number already exists. Please sign in."
            )

    # Create dedicated workspace
    workspace_id = str(ObjectId())
    now = datetime.utcnow()
    if db is not None:
        await db.workspaces.insert_one({
            "_id": workspace_id,
            "createdAt": now,
            "isDemo": False,
        })
        # Seed default catalog items for smooth onboarding
        await seed_workspace(db, workspace_id)

    # Hash PIN
    hashed_pin = hash_pin(payload.pin)
    user_id = str(ObjectId())
    user_doc = {
        "_id": user_id,
        "name": payload.name,
        "phone": payload.phone,
        "shopName": payload.shopName,
        "shopType": payload.shopType,
        "pinHash": hashed_pin,
        "workspaceId": workspace_id,
        "createdAt": now,
        "isDemo": False,
    }

    if db is not None:
        await db.users.insert_one(user_doc)

    # Set httpOnly session cookie
    response.set_cookie(
        key=COOKIE_NAME,
        value=workspace_id,
        httponly=True,
        samesite="lax",
        secure=settings.ENV != "dev",
        max_age=86400 * 30, # 30 days for real account
        path="/"
    )

    logger.info(f"Account registered successfully for {masked_phone} in workspace {workspace_id}")
    return AuthUserResponse(
        id=user_id,
        name=payload.name,
        whatsAppNumber=payload.phone,
        shopName=payload.shopName,
        shopType=payload.shopType,
        workspaceId=workspace_id,
        isDemo=False,
    )

@router.post("/auth/login", response_model=AuthUserResponse)
async def auth_login(payload: AuthLoginRequest, request: Request, response: Response):
    """
    Sign in to an existing shopkeeper account.
    - Login rate limiting per phone number and per IP
    - Lockout after 5 failed attempts (returns 429 with friendly message)
    - Returns identical error message for unknown number and wrong PIN (no account enumeration)
    - Never logs phone or PIN
    """
    masked_phone = mask_phone_for_logs(payload.phone)
    client_ip = get_client_ip_from_request(request)
    
    phone_key = f"phone:{payload.phone}"
    ip_key = f"ip:{client_ip}"

    db = get_db()

    # 1. Check if locked out
    phone_locked, phone_rem = await check_login_rate_limit(phone_key, db=db)
    ip_locked, ip_rem = await check_login_rate_limit(ip_key, db=db)
    if phone_locked or ip_locked:
        rem_sec = max(phone_rem, ip_rem)
        rem_min = max(1, rem_sec // 60)
        logger.warning(f"Login blocked due to lockout for phone {masked_phone} from IP {client_ip}")
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed login attempts. Please wait {rem_min} minute(s) before trying again."
        )

    user = None
    if db is not None:
        user = await db.users.find_one({"phone": payload.phone})

    # Common generic error message to prevent account enumeration
    GENERIC_LOGIN_ERROR = "Invalid WhatsApp number or 4-digit PIN."

    if not user:
        # Record failure on both phone and IP
        await record_failed_login(phone_key, db=db)
        is_locked, rem_sec = await record_failed_login(ip_key, db=db)
        logger.warning(f"Login failed: unknown phone {masked_phone} from IP {client_ip}")
        if is_locked:
            rem_min = max(1, rem_sec // 60)
            raise HTTPException(
                status_code=429,
                detail=f"Too many failed login attempts. Please wait {rem_min} minute(s) before trying again."
            )
        raise HTTPException(status_code=401, detail=GENERIC_LOGIN_ERROR)

    # Verify PIN
    stored_hash = user.get("pinHash", "")
    if not verify_pin(stored_hash, payload.pin):
        is_phone_locked, p_rem = await record_failed_login(phone_key, db=db)
        is_ip_locked, i_rem = await record_failed_login(ip_key, db=db)
        logger.warning(f"Login failed: incorrect PIN for phone {masked_phone} from IP {client_ip}")
        if is_phone_locked or is_ip_locked:
            rem_min = max(1, max(p_rem, i_rem) // 60)
            raise HTTPException(
                status_code=429,
                detail=f"Too many failed login attempts. Please wait {rem_min} minute(s) before trying again."
            )
        raise HTTPException(status_code=401, detail=GENERIC_LOGIN_ERROR)

    # Success: reset failed attempts
    await reset_login_attempts(phone_key, db=db)
    await reset_login_attempts(ip_key, db=db)

    workspace_id = user["workspaceId"]
    # Issue session cookie
    response.set_cookie(
        key=COOKIE_NAME,
        value=workspace_id,
        httponly=True,
        samesite="lax",
        secure=settings.ENV != "dev",
        max_age=86400 * 30, # 30 days
        path="/"
    )

    logger.info(f"User successfully logged in for {masked_phone}")
    return AuthUserResponse(
        id=str(user["_id"]),
        name=user["name"],
        whatsAppNumber=user["phone"],
        shopName=user["shopName"],
        shopType=user["shopType"],
        workspaceId=workspace_id,
        isDemo=user.get("isDemo", False),
    )

@router.get("/auth/me", response_model=Optional[AuthUserResponse])
async def get_current_user_profile(request: Request):
    """Returns profile for currently active session cookie, or None if anonymous/demo."""
    workspace_id = request.cookies.get(COOKIE_NAME)
    if not workspace_id:
        return None
    db = get_db()
    if db is not None:
        user = await db.users.find_one({"workspaceId": workspace_id})
        if user:
            return AuthUserResponse(
                id=str(user["_id"]),
                name=user["name"],
                whatsAppNumber=user["phone"],
                shopName=user["shopName"],
                shopType=user["shopType"],
                workspaceId=workspace_id,
                isDemo=user.get("isDemo", False),
            )
    return None

@router.post("/auth/logout")
async def auth_logout(response: Response):
    """Clears authentication session cookie."""
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"status": "logged_out"}


# 2. POST /api/parse
@router.post("/parse", response_model=DraftResponse)
async def parse_sale_text(
    payload: ParseRequest,
    request: Request,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """
    Runs ExtractorAgent and ValidatorAgent.
    Writes only to drafts collection with 1h TTL.
    Does NOT modify customer balances or inventory ledger.
    """
    db = get_db()
    
    # Load workspace customers and items catalog
    customers: List[Dict[str, Any]] = []
    items: List[Dict[str, Any]] = []
    
    if db is not None:
        customers = await db.customers.find({"workspaceId": workspace_id}).to_list(100)
        items = await db.items.find({"workspaceId": workspace_id}).to_list(100)

    try:
        (
            customer_info,
            draft_lines,
            issues,
            stated_total,
            computed_total,
            list_price,
            discount,
            total,
            paid,
            due,
            can_save,
            model_info,
        ) = await run_pipeline(payload.text, customers, items)
    except Exception as e:
        # Pipeline failure handling: app must never crash on bad model output
        raise HTTPException(
            status_code=500,
            detail=f"Speech extraction pipeline error: {str(e)}. You can enter fields manually."
        )

    draft_id = str(ObjectId())
    draft_doc = {
        "_id": draft_id,
        "workspaceId": workspace_id,
        "rawText": payload.text,
        "customer": customer_info,
        "lines": [l.model_dump() for l in draft_lines],
        "statedTotal": stated_total,
        "computedTotal": computed_total,
        "listPrice": list_price,
        "discount": discount,
        "total": total,
        "paid": paid,
        "due": due,
        "issues": [i.model_dump() for i in issues],
        "canSave": can_save,
        "modelInfo": model_info,
        "createdAt": datetime.utcnow(),
    }

    if db is not None:
        await db.drafts.insert_one(draft_doc)

    return DraftResponse(
        draftId=draft_id,
        rawText=payload.text,
        customer=customer_info,
        lines=draft_lines,
        statedTotal=stated_total,
        computedTotal=computed_total,
        listPrice=list_price,
        discount=discount,
        total=total,
        paid=paid,
        due=due,
        issues=issues,
        canSave=can_save,
        modelInfo=model_info,
    )

# 2b. POST /api/drafts/{draftId}/correct
@router.post("/drafts/{draftId}/correct", response_model=CorrectionResponse)
async def correct_draft(
    draftId: str,
    payload: CorrectionRequest,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """
    Feature 1: Correction by voice on DRAFTS only.
    - Validates workspace ownership of the draft.
    - Limits to max 5 corrections per draft.
    - Plans whitelisted patch operations via Gemini (or cache/heuristic).
    - If ambiguous, returns a clarifying question with tap options without mutating data.
    - Applies patch in plain Python, reruns Phase 1 validator, recomputes totals.
    - Returns updated draft and changes diff list.
    """
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")

    draft_doc = await db.drafts.find_one({"_id": draftId})
    if not draft_doc:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Workspace isolation check
    if draft_doc.get("workspaceId") != workspace_id:
        raise HTTPException(status_code=403, detail="Cross-workspace draft access denied")

    # Correction count limit: max 5 corrections
    correction_history = draft_doc.get("correctionHistory", [])
    if len(correction_history) >= 5:
        raise HTTPException(status_code=400, detail="Maximum 5 corrections reached for this draft.")

    customers = await db.customers.find({"workspaceId": workspace_id}).to_list(100)
    items = await db.items.find({"workspaceId": workspace_id}).to_list(100)

    # Ask planner for structured patch operations
    plan = await plan_correction(payload.text, draft_doc, customers, items)

    if plan.isAmbiguous:
        # Return clarifying question with 2-3 options, no changes applied
        return CorrectionResponse(
            draft=DraftResponse(
                draftId=str(draft_doc["_id"]),
                rawText=draft_doc.get("rawText", ""),
                customer=draft_doc.get("customer"),
                lines=draft_doc.get("lines", []),
                statedTotal=draft_doc.get("statedTotal"),
                computedTotal=draft_doc.get("computedTotal", 0),
                listPrice=draft_doc.get("listPrice", 0),
                discount=draft_doc.get("discount", 0),
                total=draft_doc.get("total", 0),
                paid=draft_doc.get("paid", 0),
                due=draft_doc.get("due", 0),
                issues=draft_doc.get("issues", []),
                canSave=draft_doc.get("canSave", True),
                modelInfo=draft_doc.get("modelInfo"),
            ),
            changes=[],
            isAmbiguous=True,
            clarificationQuestion=plan.ambiguityQuestion,
            clarificationOptions=plan.clarificationOptions,
            correctionCount=len(correction_history),
        )

    # Apply patch in plain Python
    updated_doc, changes = apply_patch_plan(draft_doc, plan, items, customers)

    # Rerun Phase 1 validator to recompute totals, discounts, due, issues, and canSave
    cust_name = updated_doc.get("customer", {}).get("name") if updated_doc.get("customer") else None
    cust_id = updated_doc.get("customer", {}).get("id") if updated_doc.get("customer") else None
    extractor_equivalent = ExtractorOutput(
        customerName=cust_name,
        matchedCustomerId=cust_id,
        lines=[
            ExtractedLine(
                itemName=l.get("name"),
                matchedItemId=l.get("itemId"),
                qty=l.get("qty"),
                unitPrice=l.get("unitPrice"),
            )
            for l in updated_doc.get("lines", [])
        ],
        statedTotal=updated_doc.get("statedTotal"),
        paid=updated_doc.get("paid", 0),
    )

    validated_lines, issues, list_p, disc, eff_total, due, can_save = validate_extraction(
        extractor_equivalent, items, customers, raw_text=updated_doc.get("rawText", "")
    )

    updated_doc["lines"] = [l.model_dump() for l in validated_lines]
    updated_doc["listPrice"] = list_p
    updated_doc["discount"] = disc
    updated_doc["computedTotal"] = list_p
    updated_doc["total"] = eff_total
    updated_doc["due"] = due
    updated_doc["issues"] = [i.model_dump() for i in issues]
    updated_doc["canSave"] = can_save

    # Record correction in history
    correction_entry = {
        "text": payload.text,
        "timestamp": datetime.utcnow(),
        "changes": [c.model_dump() for c in changes],
    }
    correction_history.append(correction_entry)
    updated_doc["correctionHistory"] = correction_history

    await db.drafts.replace_one({"_id": draftId}, updated_doc)

    return CorrectionResponse(
        draft=DraftResponse(
            draftId=str(updated_doc["_id"]),
            rawText=updated_doc.get("rawText", ""),
            customer=updated_doc.get("customer"),
            lines=validated_lines,
            statedTotal=updated_doc.get("statedTotal"),
            computedTotal=list_p,
            listPrice=list_p,
            discount=disc,
            total=eff_total,
            paid=updated_doc.get("paid", 0),
            due=due,
            issues=issues,
            canSave=can_save,
            modelInfo=updated_doc.get("modelInfo"),
        ),
        changes=changes,
        isAmbiguous=False,
        correctionCount=len(correction_history),
    )

# 2b. POST /api/drafts/{draftId}/patch (Feature 3: Missing-Field Prompts, No Model Call)
@router.post("/drafts/{draftId}/patch", response_model=CorrectionResponse)
async def patch_draft_direct(
    draftId: str,
    payload: PatchApplyRequest,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """
    Feature 3: Direct patch application from missing-field prompt chips (No model call).
    Applies the patch directly using apply_patch_plan in plain Python and re-runs validator.
    """
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")

    draft_doc = await db.drafts.find_one({"_id": draftId})
    if not draft_doc:
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft_doc.get("workspaceId") != workspace_id:
        raise HTTPException(status_code=403, detail="Cross-workspace draft access denied")

    customers = await db.customers.find({"workspaceId": workspace_id}).to_list(100)
    items = await db.items.find({"workspaceId": workspace_id}).to_list(100)

    plan = PatchPlan(isAmbiguous=False, operations=payload.operations)
    updated_doc, changes = apply_patch_plan(draft_doc, plan, items, customers)

    # Rerun Phase 1 validator to recompute totals, discounts, due, issues, and canSave
    cust_name = updated_doc.get("customer", {}).get("name") if updated_doc.get("customer") else None
    cust_id = updated_doc.get("customer", {}).get("id") if updated_doc.get("customer") else None
    extractor_equivalent = ExtractorOutput(
        customerName=cust_name,
        matchedCustomerId=cust_id,
        lines=[
            ExtractedLine(
                itemName=l.get("name"),
                matchedItemId=l.get("itemId"),
                qty=l.get("qty"),
                unitPrice=l.get("unitPrice"),
            )
            for l in updated_doc.get("lines", [])
        ],
        statedTotal=updated_doc.get("statedTotal"),
        paid=updated_doc.get("paid", 0),
    )

    validated_lines, issues, list_p, disc, eff_total, due, can_save = validate_extraction(
        extractor_equivalent, items, customers, raw_text=updated_doc.get("rawText", "")
    )

    updated_doc["lines"] = [l.model_dump() for l in validated_lines]
    updated_doc["listPrice"] = list_p
    updated_doc["discount"] = disc
    updated_doc["computedTotal"] = list_p
    updated_doc["total"] = eff_total
    updated_doc["due"] = due
    updated_doc["issues"] = [i.model_dump() for i in issues]
    updated_doc["canSave"] = can_save

    correction_history = draft_doc.get("correctionHistory", [])
    correction_entry = {
        "text": "Direct prompt chip action (no model call)",
        "timestamp": datetime.now(timezone.utc),
        "changes": [c.model_dump() for c in changes],
    }
    correction_history.append(correction_entry)
    updated_doc["correctionHistory"] = correction_history

    await db.drafts.replace_one({"_id": draftId}, updated_doc)

    return CorrectionResponse(
        draft=DraftResponse(
            draftId=str(updated_doc["_id"]),
            rawText=updated_doc.get("rawText", ""),
            customer=updated_doc.get("customer"),
            lines=validated_lines,
            statedTotal=updated_doc.get("statedTotal"),
            computedTotal=list_p,
            listPrice=list_p,
            discount=disc,
            total=eff_total,
            paid=updated_doc.get("paid", 0),
            due=due,
            issues=issues,
            canSave=can_save,
            modelInfo=updated_doc.get("modelInfo"),
        ),
        changes=changes,
        isAmbiguous=False,
        correctionCount=len(correction_history),
    )

# 2c. POST /api/ask
@router.post("/ask", response_model=AskResponse)
async def ask_ledger(
    payload: AskRequest,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """
    Feature 2: Ask Your Ledger
    - Question max 300 chars.
    - Read-only tools computed in plain Python and workspace-scoped on the server.
    - Workspace isolation strictly enforced: workspaceId never passed to model.
    - Numbers rule: every number in the answer comes from tool results.
    - Always returns a structured verifiable facts object.
    - Resolves customer name ambiguity with candidate tap options.
    """
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database unavailable")

    customers = await db.customers.find({"workspaceId": workspace_id}).to_list(100)
    items = await db.items.find({"workspaceId": workspace_id}).to_list(100)
    entries = await db.entries.find({"workspaceId": workspace_id}).sort("createdAt", -1).to_list(100)

    return await answer_ledger_question(payload.question, customers, items, entries)

# 3. POST /api/entries
@router.post("/entries", response_model=EntryResponse)
async def save_entry(
    payload: EntryCreateRequest,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """
    Requirement 1: Load the draft, ignore client-sent total, paid and due.
    Recompute lineTotal, total and due from the lines strictly in Python.
    Validate paid (0 <= paid <= 1_000_000, bounded) and use ONLY recomputed values.
    IDEMPOTENT: saving the same draft twice creates exactly ONE entry and returns the existing one.
    """
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database unavailable")

    # 1. Idempotency check: Draft must exist in this workspace
    draft = await db.drafts.find_one({"_id": payload.draftId, "workspaceId": workspace_id})
    if not draft:
        # Check if already processed
        existing_entry = await db.entries.find_one({"draftId": payload.draftId, "workspaceId": workspace_id})
        if existing_entry:
            customer = await db.customers.find_one({"_id": ObjectId(existing_entry["customerId"])})
            return EntryResponse(
                id=str(existing_entry["_id"]),
                workspaceId=workspace_id,
                customerId=str(existing_entry["customerId"]),
                customerName=customer["name"] if customer else existing_entry.get("customerName", "Customer"),
                lines=existing_entry["lines"],
                total=existing_entry["total"],
                paid=existing_entry["paid"],
                due=existing_entry["due"],
                rawText=existing_entry.get("rawText", ""),
                createdAt=existing_entry["createdAt"].isoformat() if isinstance(existing_entry["createdAt"], datetime) else str(existing_entry["createdAt"]),
                customerUpdatedBalance=customer.get("balance", 0) if customer else 0,
                waReceiptUrl=build_wa_receipt_url(
                    phone=customer.get("phone") if customer else None,
                    customer_name=customer["name"] if customer else "Customer",
                    lines=existing_entry["lines"],
                    total=existing_entry["total"],
                    paid=existing_entry["paid"],
                    due=existing_entry["due"]
                )
            )
        raise HTTPException(status_code=400, detail="Draft not found or expired. Please parse again.")

    # 2. Source lines & customer from draft (fallback to payload if edited lines provided)
    source_lines = payload.lines if (payload.lines and len(payload.lines) > 0) else [
        EditLineInput(
            itemId=l.get("itemId"),
            name=l.get("name"),
            qty=l.get("qty", 1),
            unitPrice=l.get("unitPrice", 0)
        ) for l in draft.get("lines", [])
    ]

    # Recompute lineTotal and overall total strictly in Python
    lines_data = []
    for line in source_lines:
        line_total = compute_line_total(line.qty, line.unitPrice)
        lines_data.append({
            "itemId": line.itemId,
            "name": line.name,
            "qty": line.qty,
            "unitPrice": line.unitPrice,
            "lineTotal": line_total
        })

    # Validate paid: bounded 0 <= paid <= 1,000,000; default to draft's validated paid
    raw_paid = payload.paid if payload.paid is not None else draft.get("paid", 0)
    if raw_paid < 0 or raw_paid > 1_000_000:
        raise HTTPException(status_code=400, detail="Paid amount must be between 0 and 1,000,000.")
    paid = int(raw_paid)

    # Ignore client-sent total & due completely: recompute in Python
    total, due = compute_entry_totals(lines_data, paid)

    # 3. Customer resolution from draft / payload
    customer_name = ""
    customer_id = None
    customer_phone = None
    if payload.customer and payload.customer.name:
        customer_name = payload.customer.name.strip()
        customer_id = payload.customer.id
        customer_phone = payload.customer.phone
    elif draft.get("customer") and draft["customer"].get("name"):
        customer_name = draft["customer"]["name"].strip()
        customer_id = draft["customer"].get("id")
        customer_phone = draft["customer"].get("phone")
    else:
        customer_name = "Cash Customer"

    customer_doc = None
    if customer_id:
        try:
            customer_doc = await db.customers.find_one({"_id": ObjectId(customer_id), "workspaceId": workspace_id})
        except Exception:
            customer_doc = None

    if not customer_doc:
        customer_doc = await db.customers.find_one({"workspaceId": workspace_id, "name": customer_name})

    if not customer_doc:
        new_cust_id = ObjectId()
        customer_doc = {
            "_id": new_cust_id,
            "workspaceId": workspace_id,
            "name": customer_name,
            "aliases": [customer_name.lower()],
            "phone": customer_phone or "",
            "balance": 0,
            "createdAt": datetime.utcnow(),
        }
        await db.customers.insert_one(customer_doc)
        customer_id = str(new_cust_id)
    else:
        customer_id = str(customer_doc["_id"])

    # 4. Atomic ledger commit using ONLY recomputed values
    new_balance = update_customer_balance(customer_doc.get("balance", 0), due)
    await db.customers.update_one(
        {"_id": customer_doc["_id"], "workspaceId": workspace_id},
        {"$set": {"balance": new_balance}}
    )

    for line in lines_data:
        if line["itemId"]:
            try:
                item_oid = ObjectId(line["itemId"])
                await db.items.update_one(
                    {"_id": item_oid, "workspaceId": workspace_id},
                    {"$inc": {"stock": -line["qty"]}}
                )
            except Exception:
                pass

    # Insert entry with status="active"
    entry_id = ObjectId()
    now = datetime.utcnow()
    entry_doc = {
        "_id": entry_id,
        "workspaceId": workspace_id,
        "draftId": payload.draftId,
        "customerId": customer_id,
        "customerName": customer_name,
        "lines": lines_data,
        "total": total,
        "paid": paid,
        "due": due,
        "status": "active",
        "rawText": draft.get("rawText", ""),
        "createdAt": now,
    }
    await db.entries.insert_one(entry_doc)

    # Delete draft to enforce single-entry idempotency
    await db.drafts.delete_one({"_id": payload.draftId, "workspaceId": workspace_id})

    # Prepare WhatsApp receipt URL
    wa_url = build_wa_receipt_url(
        phone=customer_doc.get("phone") or customer_phone,
        customer_name=customer_name,
        lines=lines_data,
        total=total,
        paid=paid,
        due=due
    )

    return EntryResponse(
        id=str(entry_id),
        workspaceId=workspace_id,
        customerId=customer_id,
        customerName=customer_name,
        lines=lines_data,
        total=total,
        paid=paid,
        due=due,
        rawText=draft.get("rawText", ""),
        createdAt=now.isoformat(),
        customerUpdatedBalance=new_balance,
        waReceiptUrl=wa_url
    )

# 3b. POST /api/entries/{entryId}/undo (Requirement 2: Undo specific entry idempotently)
@router.post("/entries/{entryId}/undo", response_model=UndoEntryResponse)
@router.post("/entries/undo", response_model=UndoEntryResponse) # backwards-compatible alias
async def undo_entry_by_id(
    entryId: Optional[str] = None,
    workspace_id: str = Depends(get_current_workspace_id)
):
    """
    Requirement 2:
    - Reject unless the entry is the most recent non-undone entry in the workspace AND within 15 minutes.
    - Mark it status="undone" with undoneAt instead of deleting.
    - Idempotent: a repeated call on an already undone entry returns the same result and never touches another entry.
    """
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database unavailable")

    target_entry = None
    if entryId:
        try:
            target_entry = await db.entries.find_one({"_id": ObjectId(entryId), "workspaceId": workspace_id})
        except Exception:
            raise HTTPException(status_code=404, detail="Entry not found in this workspace.")
        if not target_entry:
            raise HTTPException(status_code=404, detail="Entry not found in this workspace.")
    else:
        # Fallback to most recent non-undone or latest entry
        target_entry = await db.entries.find_one(
            {"workspaceId": workspace_id},
            sort=[("createdAt", -1)]
        )
        if not target_entry:
            raise HTTPException(status_code=404, detail="No entry found to undo.")

    # Idempotency check: If already undone, return existing undone result without mutating anything
    if target_entry.get("status") == "undone":
        customer_oid = ObjectId(target_entry["customerId"])
        customer = await db.customers.find_one({"_id": customer_oid, "workspaceId": workspace_id})
        current_bal = customer.get("balance", 0) if customer else 0
        return UndoEntryResponse(
            status="undone",
            undoneEntryId=str(target_entry["_id"]),
            customerName=target_entry.get("customerName", "Customer"),
            reversedDue=int(target_entry.get("due", 0)),
            customerNewBalance=current_bal,
            restoredLines=[{"name": l.get("name"), "qtyRestored": l.get("qty", 0)} for l in target_entry.get("lines", [])],
            message=f"Entry for {target_entry.get('customerName')} is already undone."
        )

    # Check whether this entry is the MOST RECENT non-undone entry in the workspace
    most_recent_active = await db.entries.find_one(
        {"workspaceId": workspace_id, "status": {"$ne": "undone"}},
        sort=[("createdAt", -1)]
    )
    if not most_recent_active or str(most_recent_active["_id"]) != str(target_entry["_id"]):
        raise HTTPException(
            status_code=400,
            detail="Only the most recent active entry in the workspace can be undone."
        )

    # Enforce 15-minute window (900 seconds)
    entry_created = target_entry["createdAt"]
    if isinstance(entry_created, str):
        try:
            entry_created = datetime.fromisoformat(entry_created)
        except Exception:
            entry_created = datetime.now(timezone.utc)
    if entry_created.tzinfo is None:
        entry_created = entry_created.replace(tzinfo=timezone.utc)
    
    age_seconds = (datetime.now(timezone.utc) - entry_created).total_seconds()
    if age_seconds > 900:  # 15 minutes
        raise HTTPException(status_code=400, detail="Undo window has expired (allowed within 15 minutes of recording).")

    customer_oid = ObjectId(target_entry["customerId"])
    customer = await db.customers.find_one({"_id": customer_oid, "workspaceId": workspace_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Associated customer record not found.")

    # 1. Reverse balance change in integer rupees
    due_amount = int(target_entry.get("due", 0))
    current_balance = int(customer.get("balance", 0))
    new_balance = current_balance - due_amount

    await db.customers.update_one(
        {"_id": customer_oid, "workspaceId": workspace_id},
        {"$set": {"balance": new_balance}}
    )

    # 2. Reverse stock decrements in plain Python
    restored_lines = []
    for line in target_entry.get("lines", []):
        qty = int(line.get("qty", 0))
        item_id = line.get("itemId")
        if item_id:
            try:
                item_oid = ObjectId(item_id)
                await db.items.update_one(
                    {"_id": item_oid, "workspaceId": workspace_id},
                    {"$inc": {"stock": qty}}
                )
                restored_lines.append({"name": line.get("name"), "qtyRestored": qty})
            except Exception:
                pass

    # 3. Mark status="undone" with undoneAt instead of deleting
    now_undone = datetime.now(timezone.utc)
    await db.entries.update_one(
        {"_id": target_entry["_id"], "workspaceId": workspace_id},
        {"$set": {
            "status": "undone",
            "undoneAt": now_undone
        }}
    )

    return UndoEntryResponse(
        status="undone",
        undoneEntryId=str(target_entry["_id"]),
        customerName=target_entry.get("customerName", "Customer"),
        reversedDue=due_amount,
        customerNewBalance=new_balance,
        restoredLines=restored_lines,
        message=f"Last entry for {target_entry.get('customerName')} undone. ₹{due_amount} udhaar reversed."
    )

# 4. GET /api/ledger
@router.get("/ledger")
async def get_ledger(workspace_id: str = Depends(get_current_workspace_id)):
    db = get_db()
    if db is None:
        return []
    entries = await db.entries.find({"workspaceId": workspace_id}).sort("createdAt", -1).to_list(100)
    for e in entries:
        e["id"] = str(e["_id"])
        e["_id"] = str(e["_id"])
        e["createdAt"] = e["createdAt"].isoformat() if isinstance(e.get("createdAt"), datetime) else str(e.get("createdAt"))
    return entries

# 5. GET /api/customers
@router.get("/customers")
async def get_customers(workspace_id: str = Depends(get_current_workspace_id)):
    db = get_db()
    if db is None:
        return []
    customers = await db.customers.find({"workspaceId": workspace_id}).sort("balance", -1).to_list(100)
    for c in customers:
        c["id"] = str(c["_id"])
        c["_id"] = str(c["_id"])
        if "createdAt" in c and isinstance(c["createdAt"], datetime):
            c["createdAt"] = c["createdAt"].isoformat()
    return customers

# 5b. POST /api/customers/match-fuzzy (Feature 4: Fuzzy Customer Matching, No Model Call)
@router.post("/customers/match-fuzzy", response_model=FuzzyMatchResponse)
async def fuzzy_match_customer(
    payload: FuzzyMatchRequest,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """
    Feature 4: Fuzzy Customer Matching (No Model Call).
    - Rapidfuzz scoring, Devanagari transliteration, lowercase & punctuation stripping.
    - Preserves honorifics ('Sharma ji' vs 'Sharma Sir' never merged).
    - Thresholds from config (>=92 auto-match, 75-92 ask, <75 new).
    - Returns near-duplicate warning if candidate scores >= 75.
    """
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database unavailable")

    customers = await db.customers.find({"workspaceId": workspace_id}).to_list(100)
    result = match_customer_fuzzy(
        query_name=payload.name,
        customers_catalog=customers,
        auto_threshold=settings.FUZZY_MATCH_AUTO_THRESHOLD,
        ask_threshold=settings.FUZZY_MATCH_ASK_THRESHOLD,
    )

    cust_candidate = None
    if result.customer:
        cust_candidate = CandidateCustomer(
            id=str(result.customer["_id"]),
            name=result.customer["name"],
            phone=result.customer.get("phone"),
            balance=result.customer.get("balance", 0),
            aliases=result.customer.get("aliases", []),
        )

    candidates_list = [
        CandidateCustomer(
            id=str(c["_id"]),
            name=c["name"],
            phone=c.get("phone"),
            balance=c.get("balance", 0),
            aliases=c.get("aliases", []),
        )
        for c in result.candidates
    ]

    return FuzzyMatchResponse(
        decision=result.decision,
        score=result.score,
        customer=cust_candidate,
        candidates=candidates_list,
        nearDuplicateWarning=result.near_duplicate_warning,
    )

# 5c. POST /api/customers/{id}/aliases (Feature 4: Add Spoken Alias with Cap)
@router.post("/customers/{customer_id}/aliases")
async def add_customer_alias(
    customer_id: str,
    payload: AddAliasRequest,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """
    Adds a confirmed spoken form as an alias on that customer.
    Cap: max 10 aliases, max 40 characters each, sanitized.
    """
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database unavailable")

    try:
        oid = ObjectId(customer_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid customer ID")

    customer = await db.customers.find_one({"_id": oid, "workspaceId": workspace_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    sanitized = sanitize_alias(payload.alias, max_length=settings.ALIAS_MAX_LENGTH)
    if not sanitized:
        raise HTTPException(status_code=400, detail="Invalid alias")

    current_aliases = customer.get("aliases", [])
    if sanitized.lower() not in [a.lower() for a in current_aliases]:
        if len(current_aliases) >= settings.ALIAS_MAX_COUNT:
            # Drop the oldest alias to respect cap
            current_aliases = current_aliases[1:]
        current_aliases.append(sanitized)
        await db.customers.update_one(
            {"_id": oid, "workspaceId": workspace_id},
            {"$set": {"aliases": current_aliases}}
        )

    return {"status": "ok", "aliases": current_aliases}

# 5c2. PATCH /api/customers/{customer_id}/phone (Optional Customer Phone Number)
@router.patch("/customers/{customer_id}/phone")
async def update_customer_phone(
    customer_id: str,
    payload: UpdateCustomerPhoneRequest,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """
    Update or set a customer's phone number.
    Validates phone: removes spaces/hyphens, ensures standard 10-13 digits.
    Makes the WhatsApp receipt and reminder flow real.
    """
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database unavailable")

    try:
        oid = ObjectId(customer_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid customer ID")

    # Clean digits
    clean_digits = "".join(ch for ch in payload.phone if ch.isdigit())
    if len(clean_digits) < 10 or len(clean_digits) > 13:
        raise HTTPException(status_code=400, detail="Phone number must contain 10 to 13 digits.")

    # Format with +91 if 10 digits
    formatted_phone = f"+91 {clean_digits}" if len(clean_digits) == 10 else f"+{clean_digits}"

    customer = await db.customers.find_one_and_update(
        {"_id": oid, "workspaceId": workspace_id},
        {"$set": {"phone": formatted_phone}},
        return_document=True
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return {
        "status": "ok",
        "customerId": customer_id,
        "phone": formatted_phone,
        "message": f"Phone number updated for {customer['name']}."
    }


# 5d. GET /api/customers/{customer_id}/reminder (Feature 5: Overdue Payment Reminder Drafts)
@router.get("/customers/{customer_id}/reminder", response_model=ReminderResponse)
async def get_customer_payment_reminder(
    customer_id: str,
    tone: str = "polite",
    workspace_id: str = Depends(get_current_workspace_id),
):
    """
    Feature 5: Overdue payment reminder drafts (no model call by default).
    Returns Hinglish reminder text formatted with customer name, due amount, last entry date,
    and a wa.me URL with URL-encoded text and digits-only phone.
    """
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database unavailable")

    try:
        oid = ObjectId(customer_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid customer ID")

    customer = await db.customers.find_one({"_id": oid, "workspaceId": workspace_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    due_balance = customer.get("balance", 0)

    # Find last entry date for customer
    last_entry = await db.entries.find_one(
        {"customerId": str(oid), "workspaceId": workspace_id},
        sort=[("createdAt", -1)]
    )
    last_entry_date = None
    if last_entry and "createdAt" in last_entry:
        dt = last_entry["createdAt"]
        last_entry_date = dt.strftime("%d %b %Y") if hasattr(dt, "strftime") else str(dt)[:10]

    selected_tone = "firm" if tone.lower() == "firm" else "polite"
    text = build_reminder_message(
        customer_name=customer["name"],
        due_amount=due_balance,
        last_entry_date=last_entry_date,
        tone=selected_tone
    )
    wa_url = build_wa_reminder_url(phone=customer.get("phone"), text=text)

    return ReminderResponse(
        customerName=customer["name"],
        balance=due_balance,
        tone=selected_tone,
        text=text,
        waUrl=wa_url
    )

# 5e. GET /api/summary/today (Feature 6: Daily Summary "Aaj Ka Hisaab")
@router.get("/summary/today", response_model=DailySummaryResponse)
async def get_today_summary(workspace_id: str = Depends(get_current_workspace_id)):
    """
    Feature 6: Daily Summary ("aaj ka hisaab").
    Computes integer rupee stats for today in Asia/Kolkata timezone:
    - entriesCount, totalSales, cashCollected, totalUdhaarGiven, topCustomer, topItem, narrative.
    - No model calls required by default.
    """
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database unavailable")

    utc_start, utc_end, date_str = get_kolkata_today_range()

    # Query entries for today within the workspace
    query = {
        "workspaceId": workspace_id,
        "createdAt": {"$gte": utc_start, "$lte": utc_end}
    }
    today_entries = await db.entries.find(query).to_list(1000)

    summary_data = compute_daily_summary(today_entries, date_str)
    return DailySummaryResponse(**summary_data)

# 6. GET /api/items
@router.get("/items")
async def get_items(workspace_id: str = Depends(get_current_workspace_id)):
    db = get_db()
    if db is None:
        return []
    items = await db.items.find({"workspaceId": workspace_id}).sort("name", 1).to_list(100)
    for i in items:
        i["id"] = str(i["_id"])
        i["_id"] = str(i["_id"])
        if "createdAt" in i and isinstance(i["createdAt"], datetime):
            i["createdAt"] = i["createdAt"].isoformat()
    return items

# 7. GET /api/entries/{id}/receipt
@router.get("/entries/{entry_id}/receipt")
async def get_receipt(entry_id: str, workspace_id: str = Depends(get_current_workspace_id)):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        oid = ObjectId(entry_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid entry ID")

    entry = await db.entries.find_one({"_id": oid, "workspaceId": workspace_id})
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found in your workspace")

    customer = await db.customers.find_one({"_id": ObjectId(entry["customerId"])})
    phone = customer.get("phone") if customer else None
    customer_name = entry.get("customerName", "Customer")

    text = format_receipt_text(
        customer_name=customer_name,
        lines=entry["lines"],
        total=entry["total"],
        paid=entry["paid"],
        due=entry["due"]
    )
    wa_url = build_wa_receipt_url(
        phone=phone,
        customer_name=customer_name,
        lines=entry["lines"],
        total=entry["total"],
        paid=entry["paid"],
        due=entry["due"]
    )

    return {"text": text, "waUrl": wa_url}

# 8. POST /api/analytics/track-click (Track WhatsApp receipt link clicks)
@router.post("/analytics/track-click")
async def track_link_click(
    payload: dict,
    workspace_id: str = Depends(get_current_workspace_id)
):
    db = get_db()
    click_type = payload.get("type", "whatsapp_receipt")
    entry_id = payload.get("entryId")
    customer_name = payload.get("customerName", "Customer")
    
    click_doc = {
        "_id": ObjectId(),
        "workspaceId": workspace_id,
        "type": click_type,
        "entryId": entry_id,
        "customerName": customer_name,
        "timestamp": datetime.utcnow()
    }
    
    if db is not None:
        await db.link_clicks.insert_one(click_doc)
        total_clicks = await db.link_clicks.count_documents({"workspaceId": workspace_id})
    else:
        total_clicks = 1

    return {"status": "ok", "totalClicks": total_clicks}

# 9. GET /api/analytics/stats (Dashboard statistics auto-updating)
@router.get("/analytics/stats")
async def get_dashboard_stats(workspace_id: str = Depends(get_current_workspace_id)):
    db = get_db()
    if db is None:
        return {
            "totalClicks": 0,
            "totalRevenue": 0,
            "totalUdhaar": 0,
            "entriesCount": 0,
            "recentClicks": []
        }
    
    total_clicks = await db.link_clicks.count_documents({"workspaceId": workspace_id})
    recent_clicks = await db.link_clicks.find(
        {"workspaceId": workspace_id}
    ).sort("timestamp", -1).limit(10).to_list(10)

    for c in recent_clicks:
        c["id"] = str(c["_id"])
        c["_id"] = str(c["_id"])
        if "timestamp" in c and isinstance(c["timestamp"], datetime):
            c["timestamp"] = c["timestamp"].isoformat()

    entries = await db.entries.find({"workspaceId": workspace_id}).to_list(500)
    total_revenue = sum(e.get("paid", 0) for e in entries)
    total_udhaar = sum(e.get("due", 0) for e in entries)
    
    return {
        "totalClicks": total_clicks,
        "totalRevenue": total_revenue,
        "totalUdhaar": total_udhaar,
        "entriesCount": len(entries),
        "recentClicks": recent_clicks
    }

# 10. POST /api/demo/reset (Requirement 3: Reset demo data, allowed ONLY if isDemo=true)
@router.post("/demo/reset")
async def reset_demo_workspace(workspace_id: str = Depends(get_current_workspace_id)):
    """
    Requirement 3:
    Only allowed when the current workspace has isDemo=true, otherwise returns HTTP 403 Forbidden.
    Resets all customers, items, drafts, and entries back to pristine demo state.
    """
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database unavailable")

    ws = await db.workspaces.find_one({"_id": workspace_id})
    if not ws or not ws.get("isDemo", False):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: /api/demo/reset is only allowed for demo workspaces."
        )

    # Wipe existing data in this demo workspace
    await db.customers.delete_many({"workspaceId": workspace_id})
    await db.items.delete_many({"workspaceId": workspace_id})
    await db.drafts.delete_many({"workspaceId": workspace_id})
    await db.entries.delete_many({"workspaceId": workspace_id})

    # Re-seed clean demo customers & catalog
    await seed_workspace(db, workspace_id)

    logger.info(f"Demo workspace {workspace_id} successfully reset.")
    return {"status": "ok", "message": "Demo workspace reset to initial sample data."}

def format_receipt_text(customer_name: str, lines: List[dict], total: int, paid: int, due: int) -> str:
    lines_str = "\n".join([f"• {l['qty']}x {l['name']} - ₹{l['lineTotal']}" for l in lines])
    return (
        f"🧾 *BolKhata Receipt*\n"
        f"👤 Customer: {customer_name}\n\n"
        f"📦 *Items:*\n{lines_str}\n\n"
        f"💰 *Total Bill:* ₹{total}\n"
        f"✅ *Paid (Jama):* ₹{paid}\n"
        f"⏳ *Baaki Udhaar:* ₹{due}\n\n"
        f"📞 Shop WhatsApp: +91 9874961805\n"
        f"_Thank you for your visit!_"
    )

def build_wa_receipt_url(phone: Optional[str], customer_name: str, lines: List[dict], total: int, paid: int, due: int) -> str:
    text = format_receipt_text(customer_name, lines, total, paid, due)
    encoded = urllib.parse.quote(text)
    clean_phone = "".join(c for c in (phone or "") if c.isdigit())
    if clean_phone:
        return f"https://wa.me/{clean_phone}?text={encoded}"
    return f"https://wa.me/?text={encoded}"

