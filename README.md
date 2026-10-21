# BolKhata (बोलखाता) — Voice-First AI Ledger for Indian Retail

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18.3.1-61dafb.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/vite-5.4-646CFF.svg)](https://vitejs.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg)](https://fastapi.tiangolo.com/)
[![MongoDB Atlas](https://img.shields.io/badge/MongoDB-Atlas-47A248.svg)](https://www.mongodb.com/atlas)
[![Gemini 2.5](https://img.shields.io/badge/Gemini-2.5--Flash-4285F4.svg)](https://ai.google.dev/)
[![Security: Tested](https://img.shields.io/badge/Security-Hardened%20%26%20Tested-success.svg)](#security--accounting-tests)

**"Bolo. Likho Mat." (Speak. Don't write.)**  
*A natural voice-entry ledger built specifically for Indian shop counters, supporting Roman Hinglish, Devanagari Hindi, and English.*

[Live Demo](#try-the-demo) • [Architecture](#core-architecture) • [Features](#key-capabilities) • [API Reference](#api-endpoints) • [Deploy Guide](#production-deployment)

</div>

---

## Overview

In traditional Indian retail (Kirana, garment stores, hardware shops), shopkeepers frequently sell on credit (*udhaar*) while their hands are busy handling cash, packaging goods, or attending multiple customers. Recording these entries manually into physical *bahi-khata* ledgers or complex ERP apps is tedious, error-prone, and often postponed until forgotten.

**BolKhata** enables shopkeepers to speak natural sentences exactly as they talk at the counter:
> *"Sharma ji ko do jeans 1800 mein di, 500 mila baaki udhaar"*  
> *"गुप्ता जी को 1 किलो चीनी और 2 पैकेट बिस्कुट, सब कैश मिला"*  
> *"Nahi, 2 jeans nahi 3 jeans karo"*

BolKhata accurately extracts customer details, items, quantities, and cash collections into structured draft cards, enables one-click voice corrections, computes balance and stock in pure Python, and sends instant formatted WhatsApp receipts.

---

## Key Capabilities

1. **Instant Voice Dictation & Natural Hinglish Extraction**
   - Transcribes voice seamlessly in the browser using the Web Speech API.
   - Dual-agent pipeline (ExtractorAgent + ValidatorAgent) powered by Google Gemini 2.5 Flash with fallback to NVIDIA NIM LLMs.
   - Handles mixed Roman Hinglish, Devanagari Hindi, Indian numeric scales, and common shop phrases.

2. **Zero-Side-Effect Draft Pipeline & Python Math Integrity**
   - **The LLM extracts; code calculates and writes.**
   - The LLM has zero direct database write access.
   - Client-sent totals, dues, and lines are strictly ignored: line totals, overall totals, dues, customer balances, and stock are recomputed in plain Python integer rupees.

3. **Voice & Text Follow-Up Correction (`POST /api/drafts/{id}/correct`)**
   - Allows shopkeepers to correct drafts effortlessly before committing (*"nahi, total 4500"*, *"Sharma Sir ko likho"*, *"paid 1000 hi hai"*).
   - Strict patch operation whitelist, structured diff tracking, and max 5 corrections per draft.

4. **"Ask Your Ledger" (`POST /api/ask`)**
   - Natural language queries over shop books (*"Sharma ji ka kitna baaki hai?"*, *"sabse zyada udhaar kiska hai?"*, *"aaj kitni bikri hui?"*).
   - Answered via read-only, workspace-isolated Python database aggregation tools with strict Numbers Rule validation.

5. **Fuzzy Customer & Alias Matching (`POST /api/customers/match-fuzzy`)**
   - Rapidfuzz phonetic and transliteration matching.
   - Honorific preservation (*"Sharma ji"* and *"Sharma Sir"* are never accidentally merged).
   - Learns and remembers custom customer aliases.

6. **Daily Summary ("Aaj Ka Hisaab", `GET /api/summary/today`)**
   - Computes total revenue, cash in hand, udhaar extended, and top-selling items strictly within the `Asia/Kolkata` calendar day.

7. **One-Click WhatsApp Receipts & Overdue Payment Reminders**
   - Formats clear, polite, cultural payment reminders and itemized receipts with direct `wa.me` links without requiring paid WhatsApp Business APIs.

8. **Enterprise-Grade Security & Multi-Tenant Isolation**
   - 100% cookie-isolated workspaces (`bolkhata_workspace_id`).
   - Argon2id password/PIN hashing with rejection of trivial/sequential PINs.
   - Login rate limiting per phone number and per IP with automatic 15-minute lockout after 5 failed attempts.
   - Strict CSRF protection with Origin validation on all state-changing endpoints.
   - 15-minute idempotent undo window (`POST /api/entries/{id}/undo`).

---

## Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React 18 + Vite)               │
│  - Web Speech API (Hands-Free Dictation)                    │
│  - Interactive Confirm Cards & Real-Time Diff Steppers      │
│  - Tailwind CSS + Framer Motion + Three.js Micro-Scenes     │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTPS / Same-Origin /api
┌──────────────────────────────▼──────────────────────────────┐
│                    FastAPI Backend Router                   │
│  - Session & CSRF Origin Validation Middleware              │
│  - Per-Workspace & Per-IP Rate Limiters                     │
│  - MongoDB Atlas Motor Async Driver                         │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
       ┌───────▼────────┐             ┌────────▼─────────┐
       │   AI Pipeline  │             │   Python Core    │
       │ (Extractor +   │             │   (Accounting,   │
       │  Validator)    │             │    Ledger, DB)   │
       └───────┬────────┘             └────────┬─────────┘
               │                               │
       ┌───────▼────────┐             ┌────────▼─────────┐
       │ Google Gemini  │             │  MongoDB Atlas   │
       │ / NVIDIA NIM   │             │  (Isolated Docs, │
       │ (LLM Services) │             │   TTL Indexes)   │
       └────────────────┘             └──────────────────┘
```

---

## Tech Stack

- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, Framer Motion, Three.js / React Three Fiber.
- **Backend:** Python 3.12+, FastAPI, Pydantic v2, Motor (Async MongoDB), Argon2-cffi, Rapidfuzz, Uvicorn.
- **Database:** MongoDB Atlas (M0 Free Tier or Dedicated Cluster).
- **AI / LLM:** Google Gemini 2.5 Flash SDK (`google-genai`), NVIDIA NIM API fallback (`OpenAI`/HTTPX interface).

---

## API Endpoints

### 1. Authentication & Workspaces
- `POST /api/session` — One-click demo workspace creation (seeds 8 customers, 12 catalog items, 24h TTL).
- `POST /api/auth/register` — Real shopkeeper registration with Argon2id PIN hashing and trivial-PIN guard.
- `POST /api/auth/login` — Secure login with per-phone and per-IP lockout protection.
- `POST /api/auth/logout` — Destroys session cookie.
- `POST /api/demo/reset` — Resets demo workspace back to pristine seed state (forbidden for real accounts).

### 2. Voice-Entry & Ledger
- `POST /api/parse` — Extracts text into a non-committing draft card (cached, customer-sanitized).
- `POST /api/drafts/{id}/correct` — Modifies draft lines/totals using conversational follow-ups.
- `POST /api/drafts/{id}/patch` — Missing-field prompts (customer chip select, item stepper).
- `POST /api/entries` — Recomputes math in Python, updates customer udhaar, decrements stock, and saves entry.
- `POST /api/entries/{id}/undo` — Reverses the most recent entry within 15 minutes (idempotent).
- `GET /api/ledger` — Lists entries scoped strictly to the caller's workspace.
- `GET /api/ledger/receipt/{id}` — Generates ready-to-share WhatsApp receipt message.

### 3. Customer & Intelligence Tools
- `GET /api/customers` — Lists customers with current balances and transaction counts.
- `POST /api/customers/match-fuzzy` — Fuzzy name matching with alias suggestions.
- `GET /api/customers/{id}/reminder` — Polite (विनम्र) or Firm (सख्त) WhatsApp reminder text with click-to-chat URL.
- `POST /api/ask` — Natural language ledger intelligence queries.
- `GET /api/summary/today` — Daily "Aaj Ka Hisaab" summary for the shop.

---

## Security & Accounting Tests

BolKhata features an automated test suite verifying accounting integrity, multi-tenant isolation, CSRF guards, and authentication defenses:

```bash
cd backend
PYTHONPATH=. ./venv/bin/pytest tests/test_new_fixes_items1_to_8.py tests/test_auth_and_security_hardening.py tests/test_accounting.py -v
```

**Test Coverage Summary (23/23 Passing):**
- `test_item1_tampered_payload_cannot_change_balance_beyond_recomputed_due`: **PASS**
- `test_item1_saving_same_draft_twice_creates_exactly_one_entry`: **PASS**
- `test_item2_undo_entry_by_id_and_idempotency`: **PASS**
- `test_item3_demo_reset_forbidden_for_real_accounts`: **PASS**
- `test_item4_cache_never_leaks_ids_across_workspaces`: **PASS**
- `test_item6_generic_workspace_mutation_rate_limit`: **PASS**
- `test_item7_csrf_origin_mismatch_rejected`: **PASS**
- `test_trivial_pin_rejection`: **PASS**
- `test_argon2_hashing_and_verification`: **PASS**
- `test_register_trivial_pin_rejected_api`: **PASS**
- `test_no_account_enumeration`: **PASS**
- `test_lockout_after_5_failed_attempts`: **PASS**
- `test_account_isolation_drafts_customers_entries`: **PASS**
- `test_per_ip_lockout_across_multiple_numbers`: **PASS**
- `test_mask_phone_never_exposes_full_number`: **PASS**
- `test_compute_line_total` & boundary validation: **PASS**
- `test_compute_entry_totals` (credit, cash, advance): **PASS**
- `test_update_customer_balance` & `test_decrement_stock`: **PASS**

---

## Local Development Setup

### Prerequisites
- Node.js 18+ & npm
- Python 3.12+
- MongoDB Atlas cluster URI or local MongoDB daemon

### 1. Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env from template
cp .env.example .env
# Edit .env with your MongoDB Atlas URI and GEMINI_API_KEY

# Start backend server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup
```bash
# In the repository root:
npm install

# Start Vite dev server on port 3000
npm run dev -- --port 3000
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Production Deployment

### Frontend (Vercel)
1. Import the repository in [Vercel](https://vercel.com).
2. Framework Preset: **Vite**.
3. Build Command: `npm run build`.
4. Output Directory: `dist`.
5. Add a `vercel.json` rewrite to route `/api/*` to your backend URL:
```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://<your-backend-app>.onrender.com/api/:path*"
    }
  ]
}
```

### Backend (Render / Railway / Docker)
1. Create a Web Service pointing to the `backend/` directory.
2. Build Command: `pip install -r requirements.txt`.
3. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
4. Configure Environment Variables:
   - `ENV`: `prod`
   - `MONGODB_URI`: `mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/bolkhata?retryWrites=true&w=majority`
   - `DATABASE_NAME`: `bolkhata`
   - `GEMINI_API_KEY`: `<your-gemini-api-key>`
   - `GEMINI_MODEL`: `gemini-2.5-flash`
   - `CORS_ORIGINS`: `https://<your-vercel-app>.vercel.app`

---

## License

This project is licensed under the [MIT License](LICENSE) — see the LICENSE file for details.
