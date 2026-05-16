"""Eval for Stage 6 — table.

SCRIPT-only. The CSV is a flattening of stage_05/*.json; the eval
verifies the flatten preserved row count and required columns, and
emits a species × study_type cross-tab so the attendee can sanity-
check the distribution by eye.

Writes stage_06/eval_script.json; prints the cross-tab.
"""
import csv
import glob
import json
import os
from collections import Counter

STAGE = "stage_06"
EXTRACTED_STAGE = "stage_05"
os.makedirs(f"{STAGE}/eval", exist_ok=True)

REQUIRED_COLUMNS = {
    "pmid", "species", "study_type", "year", "mab_name", "target",
    "format", "development_stage", "regulatory_context",
    "threeRs_mentioned", "n_animals", "duration_days",
    "species_justification", "cross_reactivity_evidence",
    "endpoints_unique_to_animal", "concurrent_nam",
    "n_nams_discussed", "author_reduction_recommendation",
    "first_author",
}

with open(f"{STAGE}/data/mabs_animal_studies.csv") as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    columns = set(reader.fieldnames or [])


SKIP_NAMES = {"eval.json", "eval_script.json", "eval_llm.json", "score.json"}

def _extracted_records():
    for p in glob.glob(f"{EXTRACTED_STAGE}/data/*.json"):
        if os.path.basename(p) in SKIP_NAMES:
            continue
        with open(p) as f:
            yield json.load(f)


# ---- script checks ----
errors = []
for r in rows:
    if not r.get("pmid"):
        errors.append("row missing pmid")
    if not r.get("species"):
        errors.append(f"row {r.get('pmid')}: missing species")
    if not r.get("study_type"):
        errors.append(f"row {r.get('pmid')}: missing study_type")
    if r.get("n_animals"):
        try:
            if int(r["n_animals"]) < 0:
                errors.append(f"row {r.get('pmid')}: negative n_animals")
        except ValueError:
            errors.append(f"row {r.get('pmid')}: non-integer n_animals")


script_checks = {
    "row_count_matches_arms":
        len(rows) == sum(len(r.get("animal_arms") or []) for r in _extracted_records()),
    "required_columns_present": REQUIRED_COLUMNS <= columns,
    "no_row_errors": not errors,
}

print("Script checks:")
for k, v in script_checks.items():
    print(f"  {'OK' if v else 'FAIL'}  {k}")
if errors:
    print("Errors:")
    for e in errors:
        print(f"    {e}")
assert all(script_checks.values()), "Stage 6 script eval failed"


# ---- cross-tab ----
crosstab = Counter((r["species"], r["study_type"]) for r in rows)
n_with_nam = sum(1 for r in rows if (r.get("concurrent_nam") or "").strip())

print(f"Rows: {len(rows)}  |  with concurrent_nam: {n_with_nam}")
print("species × study_type:")
for (sp, st), n in sorted(crosstab.items()):
    print(f"  {sp:12s} × {st:18s}  {n}")

out = f"{STAGE}/eval/eval_script.json"
with open(out, "w") as f:
    json.dump({
        "script": script_checks,
        "n_rows": len(rows),
        "n_with_concurrent_nam": n_with_nam,
        "crosstab": [
            {"species": sp, "study_type": st, "n": n}
            for (sp, st), n in crosstab.items()
        ],
        "errors": errors,
    }, f, indent=2)

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
