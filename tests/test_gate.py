import copy
import unittest
from quality.gate import evaluate

class GateTests(unittest.TestCase):
    def setUp(self):
        self.policy = {"schema_version": 1, "clients": {"atlas": ["pricing"], "beacon": ["pricing"]}}
        self.evidence = {"schema_version": 1, "run_id": "test-run", "execution_complete": True, "results": [{"client": c, "test_id": "pricing", "status": "PASS", "attempts": ["PASS"]} for c in self.policy["clients"]]}
    def blocked(self):
        self.assertEqual(evaluate(self.evidence, self.policy)["decision"], "BLOCK")
    def test_complete_pass(self):
        self.assertEqual(evaluate(self.evidence, self.policy)["decision"], "PASS")
    def test_missing_client(self):
        self.evidence["results"].pop()
        self.blocked()
    def test_duplicate(self):
        self.evidence["results"].append(copy.deepcopy(self.evidence["results"][0]))
        self.blocked()
    def test_skip_failure_and_error(self):
        for status in ["SKIP", "FAIL", "ERROR", "UNKNOWN"]:
            with self.subTest(status=status):
                self.evidence["results"][0].update(status=status, attempts=[status])
                self.blocked()
    def test_retry_does_not_mask_failure(self):
        self.evidence["results"][0]["attempts"] = ["FAIL", "PASS"]
        self.blocked()
    def test_incomplete_execution(self):
        self.evidence["execution_complete"] = False
        self.blocked()
    def test_empty_results(self):
        self.evidence["results"] = []
        self.blocked()
    def test_malformed_results(self):
        for malformed in [None, {}, [None], [{"client": []}], [{"client": "atlas", "test_id": "pricing", "status": "PASS", "attempts": []}]]:
            with self.subTest(malformed=malformed):
                self.evidence["results"] = malformed
                self.blocked()
    def test_malformed_policy(self):
        for malformed in [{}, {"schema_version": 1, "clients": {}}, {"schema_version": 1, "clients": {"atlas": []}}, {"schema_version": 1, "clients": {"atlas": ["pricing", "pricing"]}}]:
            self.assertEqual(evaluate(self.evidence, malformed)["decision"], "BLOCK")
    def test_unknown_check(self):
        self.evidence["results"][0]["test_id"] = "unexpected"
        self.blocked()
    def test_history_mismatch(self):
        self.evidence["results"][0]["status"] = "FAIL"
        self.blocked()
    def test_missing_identity_and_schema(self):
        self.evidence.pop("run_id")
        self.blocked()
        self.evidence["schema_version"] = 99
        self.blocked()
