import html
from pathlib import Path

def write_report(path, evidence, gate):
    esc = lambda value: html.escape(str(value))
    rows = "".join(f"<tr><td>{esc(r['client'])}</td><td>{esc(r['test_id'])}</td><td>{esc(r['status'])}</td><td>{esc(r['duration_ms'])}</td><td><pre>{esc(r['detail'])}</pre></td></tr>" for r in evidence["results"])
    reasons = "".join(f"<li>{esc(r)}</li>" for r in gate["reasons"])
    color = "#15803d" if gate["decision"] == "PASS" else "#b91c1c"
    document = f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Release Quality Report</title><style>body{{font:16px system-ui;background:#f1f5f9;color:#172033;margin:0;padding:32px}}main{{max-width:1100px;margin:auto;background:white;padding:28px;border-radius:12px}}h1{{margin-top:0}}.decision{{color:{color};font-size:30px;font-weight:700}}table{{border-collapse:collapse;width:100%}}td,th{{text-align:left;padding:12px;border-bottom:1px solid #cbd5e1;vertical-align:top}}pre{{white-space:pre-wrap;word-break:break-word;font-size:12px}}.scroll{{overflow:auto}}</style><main><h1>Release Quality Platform</h1><p>Synthetic order application · API and persisted-data validation</p><p class="decision">{esc(gate['decision'])}</p><p>Run: {esc(evidence['run_id'])} · Complete: {esc(evidence['execution_complete'])}</p><ul>{reasons}</ul><div class="scroll"><table><thead><tr><th>Client</th><th>Required check</th><th>Status</th><th>ms</th><th>Evidence</th></tr></thead><tbody>{rows}</tbody></table></div><p>Role values simulate permissions. This application does not implement production authentication.</p></main></html>"""
    Path(path).write_text(document)
