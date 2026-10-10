"""Validate baseline -> injected defect -> restored baseline as an executable experiment."""
import argparse
import json
from pathlib import Path
from quality.run import execute

def main(out):
    decisions = {}
    for scenario, defect in [("baseline", False), ("defect", True), ("restored", False)]:
        evidence, gate = execute(Path(out) / scenario, defect)
        decisions[scenario] = gate["decision"]
        if scenario == "defect":
            failures = {(r["client"], r["test_id"]) for r in evidence["results"] if r["status"] != "PASS"}
            if ("beacon", "pricing") not in failures or any(c != "beacon" for c, _ in failures):
                raise RuntimeError(f"Unexpected defect detection: {failures}")
    if decisions != {"baseline": "PASS", "defect": "BLOCK", "restored": "PASS"}:
        raise RuntimeError(f"Demonstration failed: {decisions}")
    (Path(out) / "summary.json").write_text(json.dumps(decisions, indent=2) + "\n")
    print(json.dumps(decisions, indent=2))
    print("Restored means rerun with the synthetic defect switch disabled.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="reports/demo")
    main(parser.parse_args().out)
