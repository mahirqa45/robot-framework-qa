"""Fail-closed evaluation of required client/test evidence."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def evaluate(evidence, policy):
    reasons = []
    if not isinstance(policy, dict) or policy.get("schema_version") != 1 or not isinstance(policy.get("clients"), dict) or not policy["clients"]:
        return {"decision": "BLOCK", "reasons": ["Invalid or empty policy"]}
    required = set()
    for client, tests in policy["clients"].items():
        if not isinstance(client, str) or not client or not isinstance(tests, list) or not tests or any(not isinstance(t, str) or not t for t in tests) or len(set(tests)) != len(tests):
            return {"decision": "BLOCK", "reasons": ["Invalid required-test manifest"]}
        required.update((client, t) for t in tests)
    if not isinstance(evidence, dict) or evidence.get("schema_version") != 1:
        return {"decision": "BLOCK", "reasons": ["Invalid evidence schema"]}
    if evidence.get("execution_complete") is not True:
        reasons.append("Execution incomplete")
    if not isinstance(evidence.get("run_id"), str) or not evidence["run_id"]:
        reasons.append("Missing run identity")
    records = evidence.get("results")
    if not isinstance(records, list):
        return {"decision": "BLOCK", "reasons": reasons + ["Results must be a list"]}
    seen = set()
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("client"), str) or not isinstance(record.get("test_id"), str):
            reasons.append("Malformed result record")
            continue
        key = record["client"], record["test_id"]
        label = "/".join(key)
        if key in seen:
            reasons.append(f"Duplicate result: {label}")
        seen.add(key)
        if key not in required:
            reasons.append(f"Unexpected result: {label}")
        attempts = record.get("attempts")
        if not isinstance(attempts, list) or not attempts or any(a not in ("PASS", "FAIL", "ERROR", "SKIP") for a in attempts):
            reasons.append(f"Invalid attempt history: {label}")
        elif any(a != "PASS" for a in attempts):
            reasons.append(f"Required check not clean: {label} ({','.join(attempts)})")
        if record.get("status") not in ("PASS", "FAIL", "ERROR", "SKIP"):
            reasons.append(f"Unknown status: {label}")
        elif isinstance(attempts, list) and attempts and record["status"] != attempts[-1]:
            reasons.append(f"Status/history mismatch: {label}")
    reasons.extend(f"Missing required check: {c}/{t}" for c, t in sorted(required - seen))
    return {"decision": "BLOCK" if reasons else "PASS", "reasons": reasons}

def load_policy():
    return json.loads((ROOT / "policies/release.json").read_text())
