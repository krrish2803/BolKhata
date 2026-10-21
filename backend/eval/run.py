import json
import asyncio
import os
import sys
import argparse
import hashlib
from bson import ObjectId

from app.seed import SEED_CUSTOMERS, SEED_ITEMS
from app.agents.pipeline import run_pipeline
from app.config import settings

def compute_sha256(filepath: str) -> str:
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def find_file(relative_paths: list) -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(base_dir, "../.."))
    for p in relative_paths:
        candidate1 = os.path.join(project_root, p)
        if os.path.exists(candidate1):
            return candidate1
        candidate2 = os.path.join(base_dir, os.path.basename(p))
        if os.path.exists(candidate2):
            return candidate2
    return os.path.join(project_root, relative_paths[0])

async def evaluate(allow_fallback: bool = False, update_lock: bool = False, provider: str = "auto", max_cases: int = 0):
    dev_json_path = find_file(["eval/dev.json", "backend/eval/dev.json", "backend/eval/cases.json"])
    dev_lock_path = find_file(["eval/dev.lock", "backend/eval/dev.lock"])
    results_path = find_file(["eval/results.json", "backend/eval/results.json"])

    if not os.path.exists(dev_json_path):
        raise FileNotFoundError(f"Evaluation dataset not found at {dev_json_path}")

    current_hash = compute_sha256(dev_json_path)

    # 1. Freeze the eval lock check
    if update_lock:
        with open(dev_lock_path, "w", encoding="utf-8") as f:
            f.write(current_hash + "\n")
        # Also sync to backend/eval/dev.lock if different
        alt_lock = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dev.lock")
        if alt_lock != dev_lock_path:
            with open(alt_lock, "w", encoding="utf-8") as f:
                f.write(current_hash + "\n")
        print(f"🔒 Updated eval lock to SHA-256: {current_hash}")
    else:
        if not os.path.exists(dev_lock_path):
            raise RuntimeError(f"Lock file not found at {dev_lock_path}. Run with --update-lock to initialize.")
        with open(dev_lock_path, "r", encoding="utf-8") as f:
            expected_hash = f.read().strip()
        if current_hash != expected_hash:
            raise RuntimeError(
                f"EVAL INTEGRITY ERROR: Hash of {dev_json_path} ({current_hash}) does not match {dev_lock_path} ({expected_hash}). "
                "Refusing to run unless --update-lock is passed. Do not edit cases to make results pass!"
            )

    with open(dev_json_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    if max_cases > 0:
        cases = cases[:max_cases]

    # Prepare seed catalogs
    customers_catalog = [
        {"_id": ObjectId(), "name": c["name"], "aliases": c.get("aliases", []), "phone": c.get("phone"), "balance": c.get("balance", 0)}
        for c in SEED_CUSTOMERS
    ]
    items_catalog = [
        {"_id": ObjectId(), "name": i["name"], "aliases": i.get("aliases", []), "price": i["price"], "stock": i.get("stock", 50)}
        for i in SEED_ITEMS
    ]

    total_cases = len(cases)

    # Accounting structures per engine
    # Every case ends as exactly ONE of PASS, FAIL, ERROR (with reason), or SKIPPED (with reason)
    engine_cases = {}   # engine -> list of case IDs
    engine_stats = {}   # engine -> {PASS: int, FAIL: int, ERROR: int, SKIPPED: int}
    
    case_outcomes = []
    failures = []
    errors = []
    skipped = []

    rpm = getattr(settings, "GEMINI_RPM", 4)
    throttle_interval = 60.0 / max(1, rpm)

    # Configure provider if requested
    if provider == "gemini":
        settings.PRIMARY_PROVIDER = "gemini"
        settings.PRIMARY_MODEL = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
        settings.SECONDARY_PROVIDER = ""
        settings.SECONDARY_MODEL = ""
    elif provider == "nvidia":
        settings.PRIMARY_PROVIDER = "nvidia"
        settings.PRIMARY_MODEL = getattr(settings, "NVIDIA_MODEL", "meta/llama-3.2-11b-vision-instruct")
        settings.SECONDARY_PROVIDER = ""
        settings.SECONDARY_MODEL = ""

    print(f"\n=======================================================")
    print(f"  BolKhata Frozen Eval: {total_cases} test cases")
    print(f"  Dataset: {dev_json_path}")
    print(f"  SHA-256: {current_hash}")
    print(f"  Primary Engine: {settings.PRIMARY_PROVIDER}:{settings.PRIMARY_MODEL} (Throttled: {rpm} RPM)")
    print(f"  Allow fallback: {allow_fallback}")
    print(f"=======================================================\n")

    for idx, case in enumerate(cases):
        case_id = case.get("id", f"case-{idx+1}")
        text = case["text"]
        expected = case.get("expected")

        if not expected:
            engine = "none"
            outcome = "SKIPPED"
            reason = "No expected outcome defined in case fixture"
            skipped.append({"id": case_id, "reason": reason})
            engine_stats.setdefault(engine, {"PASS": 0, "FAIL": 0, "ERROR": 0, "SKIPPED": 0})["SKIPPED"] += 1
            engine_cases.setdefault(engine, []).append(case_id)
            print(f"[{idx+1:02d}/{total_cases:02d}] ⏭ SKIPPED ({case_id}) | {reason}")
            continue

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
            ) = await run_pipeline(
                text,
                customers_catalog,
                items_catalog,
                allow_fallback=allow_fallback
            )

            is_fallback = model_info.get("isFallback", False)
            source = model_info.get("source", "unknown")
            model_name = model_info.get("model", "unknown")
            latency = model_info.get("latencyMs", 0)

            # Determine engine tag
            engine = source.lower() if source else "unknown"

            # Check matching
            extracted_cust_name = customer_info["name"] if customer_info else None
            cust_match = (
                extracted_cust_name is not None and
                (expected["customer"].lower() in extracted_cust_name.lower() or
                 extracted_cust_name.lower() in expected["customer"].lower())
            )

            extracted_item_names = [l.name.lower() for l in draft_lines]
            expected_item_names = [l["name"].lower() for l in expected["lines"]]
            items_match = (
                len(extracted_item_names) == len(expected_item_names) and
                all(any(exp in ext for ext in extracted_item_names) for exp in expected_item_names)
            )

            quantities_match = (
                len(draft_lines) == len(expected["lines"]) and
                sum(l.qty for l in draft_lines) == sum(l["qty"] for l in expected["lines"])
            )

            total_match = (total == expected["total"])
            paid_match = (paid == expected["paid"])
            due_match = (due == expected["due"])

            is_perfect = (
                cust_match and
                items_match and
                quantities_match and
                total_match and
                paid_match and
                due_match
            )

            if is_fallback and not allow_fallback:
                outcome = "ERROR"
                reason = "Fallback occurred when allow_fallback was False"
                errors.append({"id": case_id, "reason": reason, "engine": engine})
            elif is_perfect:
                outcome = "PASS"
                reason = None
            else:
                outcome = "FAIL"
                failed_fields = [
                    k for k, matched in [
                        ("customer", cust_match),
                        ("items", items_match),
                        ("quantities", quantities_match),
                        ("total", total_match),
                        ("paid", paid_match),
                        ("due", due_match),
                    ] if not matched
                ]
                reason = f"Failed fields: {failed_fields}"
                failures.append({
                    "id": case_id,
                    "caseIndex": idx + 1,
                    "engine": engine,
                    "model": model_name,
                    "text": text,
                    "failedFields": failed_fields,
                    "expected": expected,
                    "got": {
                        "customer": extracted_cust_name,
                        "lines": [{"name": l.name, "qty": l.qty, "price": l.unitPrice} for l in draft_lines],
                        "total": total,
                        "paid": paid,
                        "due": due,
                    }
                })

            engine_stats.setdefault(engine, {"PASS": 0, "FAIL": 0, "ERROR": 0, "SKIPPED": 0})[outcome] += 1
            engine_cases.setdefault(engine, []).append(case_id)

            icon = "✓ PASS" if outcome == "PASS" else ("✗ FAIL" if outcome == "FAIL" else "⚠ ERROR")
            print(f"[{idx+1:02d}/{total_cases:02d}] {icon} [{engine} | {latency}ms] ({case_id}): \"{text[:45]}...\"")

            case_outcomes.append({
                "id": case_id,
                "index": idx + 1,
                "engine": engine,
                "model": model_name,
                "outcome": outcome,
                "reason": reason,
                "latencyMs": latency,
                "text": text,
            })

        except Exception as e:
            engine = settings.PRIMARY_PROVIDER.lower()
            outcome = "ERROR"
            reason = str(e)
            errors.append({"id": case_id, "reason": reason, "engine": engine})
            engine_stats.setdefault(engine, {"PASS": 0, "FAIL": 0, "ERROR": 0, "SKIPPED": 0})["ERROR"] += 1
            engine_cases.setdefault(engine, []).append(case_id)
            print(f"[{idx+1:02d}/{total_cases:02d}] ✗ ERROR [{engine}] ({case_id}): {e}")
            case_outcomes.append({
                "id": case_id,
                "index": idx + 1,
                "engine": engine,
                "model": "unknown",
                "outcome": outcome,
                "reason": reason,
                "latencyMs": 0,
                "text": text,
            })

    # Headlines per engine: PASS of (PASS+FAIL)
    headlines = {}
    for eng, st in engine_stats.items():
        pass_fail_total = st["PASS"] + st["FAIL"]
        pct = round((st["PASS"] / pass_fail_total) * 100, 1) if pass_fail_total > 0 else 0.0
        headlines[eng] = f"{st['PASS']} of {pass_fail_total} on {eng} ({pct}%)"

    results_data = {
        "datasetSha256": current_hash,
        "datasetPath": dev_json_path,
        "totalCases": total_cases,
        "headlines": headlines,
        "engineStats": engine_stats,
        "engineCases": engine_cases,
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
        "caseAuditLog": case_outcomes,
    }

    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2)

    print("\n-------------------------------------------------------")
    print(f"FROZEN EVALUATION RESULTS (SHA-256: {current_hash[:12]}...):")
    for eng, hl in headlines.items():
        st = engine_stats[eng]
        sum_counts = st["PASS"] + st["FAIL"] + st["ERROR"] + st["SKIPPED"]
        print(f"🎯 Engine [{eng}]: {hl}")
        print(f"   Counts: PASS={st['PASS']}, FAIL={st['FAIL']}, ERROR={st['ERROR']}, SKIPPED={st['SKIPPED']} (Total={sum_counts})")
        print(f"   Case IDs on {eng}: {', '.join(engine_cases[eng])}\n")

    print(f"Results saved to: {results_path}")
    print("-------------------------------------------------------\n")
    return results_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-fallback", action="store_true", help="Allow fallback to rule-based parser on model failure")
    parser.add_argument("--update-lock", action="store_true", help="Update the eval lock hash to match dev.json")
    parser.add_argument("--provider", type=str, default="auto", choices=["auto", "gemini", "nvidia"], help="Target provider for eval")
    parser.add_argument("--max-cases", type=int, default=0, help="Max cases to run (0 for all)")
    args = parser.parse_args()

    asyncio.run(evaluate(
        allow_fallback=args.allow_fallback,
        update_lock=args.update_lock,
        provider=args.provider,
        max_cases=args.max_cases
    ))
