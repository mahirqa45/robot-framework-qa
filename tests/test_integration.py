import json
import tempfile
import unittest
from pathlib import Path
from quality.run import execute
from app.service import OrderService

class IntegrationTests(unittest.TestCase):
    def test_baseline_and_client_defect(self):
        with tempfile.TemporaryDirectory() as folder:
            baseline, gate = execute(Path(folder) / "baseline")
            self.assertEqual(len(baseline["results"]), 18)
            self.assertEqual(gate["decision"], "PASS")
            defect, gate = execute(Path(folder) / "defect", defect=True)
            self.assertEqual(gate["decision"], "BLOCK")
            failures = {(r["client"], r["test_id"]) for r in defect["results"] if r["status"] != "PASS"}
            self.assertIn(("beacon", "pricing"), failures)
            self.assertTrue(all(c == "beacon" for c, _ in failures))
            self.assertEqual(json.loads((Path(folder) / "defect/gate.json").read_text())["decision"], "BLOCK")
            self.assertIn("BLOCK", (Path(folder) / "defect/report.html").read_text())
    def test_client_scope_is_explicit(self):
        with tempfile.TemporaryDirectory() as folder:
            evidence, gate = execute(folder, clients=["cedar"])
            self.assertEqual(len(evidence["results"]), 6)
            self.assertEqual(gate["scope"], "client-only")
            self.assertEqual(gate["decision"], "PASS")
    def test_database_survives_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            database = str(Path(folder) / "orders.sqlite")
            service = OrderService(database)
            order = service.create("atlas", {"role": "buyer", "unit_price": 100, "quantity": 2})
            service.close()
            reopened = OrderService(database)
            try:
                self.assertEqual(reopened.get("atlas", order["id"]), order)
            finally:
                reopened.close()
