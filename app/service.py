"""Synthetic order service: integer currency, client scoping, injectable regression."""
import json
import sqlite3
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class DomainError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)

class OrderService:
    def __init__(self, database=":memory:", inject_discount_defect=False):
        self.profiles = json.loads((ROOT / "clients/profiles.json").read_text())
        self.inject_discount_defect = inject_discount_defect
        self.lock = threading.RLock()
        self.db = sqlite3.connect(database, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, client TEXT NOT NULL, role TEXT NOT NULL, subtotal INTEGER NOT NULL, discount INTEGER NOT NULL, tax INTEGER NOT NULL, total INTEGER NOT NULL, approval_required INTEGER NOT NULL)")
        self.db.commit()

    def close(self):
        self.db.close()

    def profile(self, client):
        if client not in self.profiles:
            raise DomainError(404, "Unknown client")
        return self.profiles[client]

    def create(self, client, payload):
        profile = self.profile(client)
        if not isinstance(payload, dict):
            raise DomainError(400, "Expected a JSON object")
        role = payload.get("role")
        if role not in profile["roles"]:
            raise DomainError(403, "Role cannot create orders")
        amount, quantity = payload.get("unit_price"), payload.get("quantity")
        if type(amount) is not int or type(quantity) is not int or not (1 <= amount <= 1000000) or not (1 <= quantity <= 100):
            raise DomainError(400, "unit_price and quantity must be bounded positive integers")
        subtotal = amount * quantity
        discount_bps = profile["discount_bps"]
        if self.inject_discount_defect and client == "beacon":
            discount_bps = 0
        # Half-up rounding for non-negative integer minor units.
        discount = (subtotal * discount_bps + 5000) // 10000
        tax = ((subtotal - discount) * profile["tax_bps"] + 5000) // 10000
        total = subtotal - discount + tax
        approval = total > profile["approval_threshold"]
        with self.lock:
            cursor = self.db.execute("INSERT INTO orders (client, role, subtotal, discount, tax, total, approval_required) VALUES (?, ?, ?, ?, ?, ?, ?)", (client, role, subtotal, discount, tax, total, int(approval)))
            self.db.commit()
            return self.get(client, cursor.lastrowid)

    def get(self, client, order_id):
        self.profile(client)
        with self.lock:
            row = self.db.execute("SELECT * FROM orders WHERE id=? AND client=?", (order_id, client)).fetchone()
        if row is None:
            raise DomainError(404, "Order not found")
        result = dict(row)
        result["approval_required"] = bool(result["approval_required"])
        return result
