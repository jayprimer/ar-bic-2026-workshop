"""Eval for Stage 2 — script checks only (no API key needed).

Deterministic re-checks of stage_02/screened.json shape:
  - every record has a PMID
  - verdict is in {include, exclude}
  - rationale is a non-empty string

Writes stage_02/eval_script.json and merges a `script` block into
stage_02/score.json. Companion to eval_02_llm.py.
"""
import json
import os

STAGE = "stage_02"
os.makedirs(f"{STAGE}/eval", exist_ok=True)

with open(f"{STAGE}/data/screened.json") as f:
    recs = json.load(f)


script_checks = {
    "every_record_has_pmid": all(r.get("pmid") for r in recs),
    "verdicts_valid": all(r.get("verdict") in {"include", "exclude"} for r in recs),
    "rationales_non_empty": all((r.get("rationale") or "").strip() for r in recs),
}

print("Script checks:")
for k, v in script_checks.items():
    print(f"  {'OK' if v else 'FAIL'}  {k}")

out = f"{STAGE}/eval/eval_script.json"
with open(out, "w") as f:
    json.dump({"script": script_checks}, f, indent=2)
print(f"Wrote {out}")


def write_score(stage, key, passed, total):
    """Merge {passed, total, percent} under `key` into stage/data/score.json."""
    path = f"{stage}/eval/score.json"
    data = {}
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
    pct = round(100.0 * passed / total, 1) if total else 0.0
    data[key] = {"passed": passed, "total": total, "percent": pct}
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  score: {key} {passed}/{total} ({pct}%)")


write_score(STAGE, "script",
            sum(1 for v in script_checks.values() if v),
            len(script_checks))

assert all(script_checks.values()), "Stage 2 script eval failed"
