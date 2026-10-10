"""Run real HTTP checks, record normalized evidence, and enforce the release gate."""
import argparse
import json
import threading
import time
import traceback
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from app.server import Server
from app.service import OrderService
from quality.gate import evaluate, load_policy
from quality.report import write_report

# Expectations are independent from application configuration.
EXPECTED = {"atlas": (0, 0, 100000, "buyer"), "beacon": (1000, 0, 50000, "buyer"), "cedar": (0, 1800, 75000, "admin")}

def request(base, client, payload=None, order_id=None, raw=None):
    path = f"/clients/{client}/orders" + (f"/{order_id}" if order_id is not None else "")
    data = raw if raw is not None else (json.dumps(payload).encode() if payload is not None else None)
    req = Request(base + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=5) as response:
            return response.status, json.load(response)
    except HTTPError as response:
        return response.code, json.load(response)

def require(condition, message):
    if not condition:
        raise AssertionError(message)

def checks(base, client, service):
    discount_bps, tax_bps, threshold, role = EXPECTED[client]
    def create(amount=10000, quantity=2):
        code, order = request(base, client, {"role": role, "unit_price": amount, "quantity": quantity})
        require(code == 201, f"Expected 201, got {code}: {order}")
        return order
    def pricing():
        order = create()
        totals = {"atlas": 20000, "beacon": 18000, "cedar": 23600}
        discounts = {"atlas": 0, "beacon": 2000, "cedar": 0}
        taxes = {"atlas": 0, "beacon": 0, "cedar": 3600}
        for field, expected in [("subtotal", 20000), ("total", totals[client]), ("discount", discounts[client]), ("tax", taxes[client])]:
            require(order[field] == expected, f"{field}: expected {expected}, got {order[field]}")
        odd = create(5, 1)
        expected_odd = {"atlas": 5, "beacon": 4, "cedar": 6}
        require(odd["total"] == expected_odd[client], "Half-up rounding mismatch")
    def permissions():
        for allowed in (["admin"] if client == "cedar" else ["buyer", "admin"]):
            code, _ = request(base, client, {"role": allowed, "unit_price": 100, "quantity": 1})
            require(code == 201, f"Allowed role {allowed}: {code}")
        for denied in (["viewer", "buyer"] if client == "cedar" else ["viewer"]):
            code, _ = request(base, client, {"role": denied, "unit_price": 100, "quantity": 1})
            require(code == 403, f"Denied role {denied}: {code}")
    def persistence():
        order = create()
        code, fetched = request(base, client, order_id=order["id"])
        require(code == 200 and fetched == order, "GET does not match created order")
        with service.lock:
            row = dict(service.db.execute("SELECT * FROM orders WHERE id=?", (order["id"],)).fetchone())
        require(row["client"] == client and row["total"] == order["total"], "Persisted data mismatch")
    def isolation():
        order = create()
        for other in EXPECTED:
            if other != client:
                code, _ = request(base, other, order_id=order["id"])
                require(code == 404, f"Order leaked to {other}")
    def validation():
        for value in [0, -1, True, 1.5, "100", 1000001]:
            code, _ = request(base, client, {"role": role, "unit_price": value, "quantity": 1})
            require(code == 400, f"Invalid price {value!r}: {code}")
        for value in [0, -1, True, 101]:
            code, _ = request(base, client, {"role": role, "unit_price": 100, "quantity": value})
            require(code == 400, f"Invalid quantity {value!r}: {code}")
        code, _ = request(base, client, raw=b"{broken")
        require(code == 400, "Malformed JSON accepted")
        code, _ = request(base, "unknown", {"role": role, "unit_price": 100, "quantity": 1})
        require(code == 404, "Unknown client accepted")
    def approval_boundary():
        # Independently calculate the first subtotal exceeding the client threshold.
        def expected_total(amount):
            discount = (amount * discount_bps + 5000) // 10000
            return amount - discount + ((amount - discount) * tax_bps + 5000) // 10000
        lo, hi = 1, 1000000
        while lo < hi:
            mid = (lo + hi) // 2
            if expected_total(mid) > threshold:
                hi = mid
            else:
                lo = mid + 1
        require(create(lo - 1, 1)["approval_required"] is False, "Approval triggered at/below threshold")
        require(create(lo, 1)["approval_required"] is True, "Approval missing above threshold")
    return {"pricing": pricing, "permissions": permissions, "persistence": persistence, "isolation": isolation, "validation": validation, "approval_boundary": approval_boundary}

def execute(out, defect=False, clients=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    evidence = {"schema_version": 1, "run_id": str(uuid.uuid4()), "execution_complete": False, "results": [], "scenario": "discount-defect" if defect else "baseline"}
    service = OrderService(inject_discount_defect=defect)
    server = Server(service)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        for client in (clients or list(EXPECTED)):
            for test_id, check in checks(base, client, service).items():
                start = time.perf_counter()
                status, detail = "PASS", "Assertions satisfied"
                try:
                    check()
                except AssertionError as error:
                    status, detail = "FAIL", str(error)
                except Exception:
                    status, detail = "ERROR", traceback.format_exc()
                evidence["results"].append({"client": client, "test_id": test_id, "status": status, "attempts": [status], "duration_ms": round((time.perf_counter() - start) * 1000, 2), "detail": detail})
        evidence["execution_complete"] = True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        service.close()
    policy = load_policy()
    # A scoped run evaluates only the selected clients; full release certification requires all clients.
    if clients:
        policy = {**policy, "clients": {c: policy["clients"][c] for c in clients}}
    gate = evaluate(evidence, policy)
    gate["scope"] = "client-only" if clients else "full-release"
    (out / "results.json").write_text(json.dumps(evidence, indent=2) + "\n")
    (out / "gate.json").write_text(json.dumps(gate, indent=2) + "\n")
    write_report(out / "report.html", evidence, gate)
    return evidence, gate

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="reports/latest")
    parser.add_argument("--inject-discount-defect", action="store_true")
    parser.add_argument("--client", choices=list(EXPECTED))
    args = parser.parse_args()
    evidence, gate = execute(args.out, args.inject_discount_defect, [args.client] if args.client else None)
    print(f"{gate['decision']} ({gate['scope']}): {len(evidence['results'])} checks; report: {args.out}/report.html")
    for reason in gate["reasons"]:
        print(f"  - {reason}")
    raise SystemExit(0 if gate["decision"] == "PASS" else 1)
