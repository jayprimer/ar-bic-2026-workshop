"""Eval for Stage 3 — fulltext download.

SCRIPT-only. Stage 3 is mechanical (lookup + download); the eval
checks every included PMID landed as exactly one of:
  .pdf or .xml  fulltext from PMC OA
  .json         metadata-only fallback (paper not OA in PMC)

and that the file is sensibly sized on disk. Coverage is summarized
as fulltext vs metadata-only.

Writes stage_03/eval_script.json + merges a `script` block into
stage_03/score.json.
"""
import json
import os

STAGE = "stage_03"
os.makedirs(f"{STAGE}/eval", exist_ok=True)

with open("stage_02/data/screened.json") as f:
    included = [r for r in json.load(f) if r["verdict"] == "include"]
with open(f"{STAGE}/data/fetched.json") as f:
    fetched = json.load(f)


def _kind(path):
    if not path:
        return "missing"
    if path.endswith(".pdf"):
        return "pdf"
    if path.endswith(".xml"):
        return "xml"
    if path.endswith(".json"):
        return "metadata"
    return "unknown"


# ---- script checks ----
errors = []
for pmid, path in fetched.items():
    if not path:
        errors.append(f"{pmid}: no path written")
        continue
    if not os.path.exists(path):
        errors.append(f"{pmid} -> {path} missing on disk")
        continue
    size = os.path.getsize(path)
    floor = 100 if path.endswith(".json") else 10_000
    if size < floor:
        errors.append(f"{pmid} -> {path} suspiciously small ({size} bytes, floor {floor})")

n_inc  = len(included)
n_pdf  = sum(1 for v in fetched.values() if v and v.endswith(".pdf"))
n_xml  = sum(1 for v in fetched.values() if v and v.endswith(".xml"))
n_meta = sum(1 for v in fetched.values() if v and v.endswith(".json"))
n_full = n_pdf + n_xml
n_unaccounted = n_inc - n_full - n_meta

script_checks = {
    "every_included_pmid_has_entry":
        set(r["pmid"] for r in included) <= set(fetched.keys()),
    "every_pmid_has_artifact":
        all(v for v in fetched.values()),
    "no_missing_or_undersized_files": not errors,
    "fulltext_coverage_realistic":
        # >0 fulltext hits means oa.fcgi is working; if 100% metadata-only,
        # the OA path has broken upstream.
        0 < n_full <= n_inc if n_inc else True,
    "kinds_account_for_all_pmids":
        n_unaccounted == 0,
}

print("Script checks:")
for k, v in script_checks.items():
    print(f"  {'OK' if v else 'FAIL'}  {k}")
if errors:
    print("Errors:")
    for e in errors:
        print(f"    {e}")
assert all(script_checks.values()), "Stage 3 script eval failed"

summary = {
    "included":          n_inc,
    "fulltext":          n_full,
    "pdf":               n_pdf,
    "xml":               n_xml,
    "metadata_only":     n_meta,
    "fulltext_ratio":    round(n_full / n_inc, 3) if n_inc else 0.0,
    "errors":            errors,
}

out = f"{STAGE}/eval/eval_script.json"
with open(out, "w") as f:
    json.dump({"script": script_checks, "summary": summary}, f, indent=2)

print(f"Coverage: {n_full}/{n_inc} fulltext "
      f"({n_pdf} PDF + {n_xml} XML), "
      f"{n_meta} metadata-only fallback(s)")
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

print("Manual follow-up: open one fetched article and confirm it's "
      "the expected mAb paper, not a corrigendum / supplement.")
