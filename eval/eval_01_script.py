"""Eval for Stage 1 — script checks only (no API key needed).

Deterministic re-checks of stage_01/data/pmids.json:
  - PMID-list shape (non-empty, numeric, no dupes, count <= cap,
    records align with pmids order)
  - per-record metadata completeness (all 8 required keys present,
    titles substantive, no XML-tag leakage in abstracts,
    abstract/author coverage above thresholds, journal/year/pub_types
    populated)

Writes stage_01/data/eval_script.json. Companion to eval_01_llm.py,
which runs the AI rubric.
"""
import datetime
import json
import os
import re

# Match suspected XML-tag leakage: an angle bracket immediately
# followed (with optional slash) by an ASCII letter — `<i>`, `</sub>`,
# `<sup>`. Plain math comparisons like `>10`, `< 0.01`, `>99%` don't
# match.
XML_TAG_LEAK = re.compile(r"</?[a-zA-Z]")

STAGE = "stage_01"
os.makedirs(f"{STAGE}/eval", exist_ok=True)

REQUIRED_FIELDS = {
    "pmid", "title", "abstract", "authors", "first_author",
    "journal", "year", "pub_types",
}
THIS_YEAR = datetime.date.today().year

with open(f"{STAGE}/data/pmids.json") as f:
    doc = json.load(f)
pmids = doc["pmids"]
records = doc.get("records") or []


# ---- PMID-list shape ----
script_checks = {
    "pmids_non_empty": bool(pmids),
    "all_numeric": all(p.isdigit() for p in pmids),
    "no_duplicates": len(pmids) == len(set(pmids)),
    "respects_cap": len(pmids) <= doc.get("n_requested", len(pmids)),
    "records_match_pmids": [r["pmid"] for r in records] == pmids,
}


# ---- per-record metadata completeness ----
per_record_issues = []
n_fields_present = 0
n_title_ok = 0
n_abstract_long = 0
n_abstract_no_xml_leak = 0
n_authors_non_empty = 0
n_journal_ok = 0
n_year_ok = 0
n_pubtypes_ok = 0

for r in records:
    issues = []
    if set(r.keys()) >= REQUIRED_FIELDS:
        n_fields_present += 1
    else:
        issues.append(f"missing keys: {REQUIRED_FIELDS - set(r.keys())}")

    if r.get("title") and len(r["title"]) > 10:
        n_title_ok += 1
    else:
        issues.append("title missing or < 10 chars")

    abstract = r.get("abstract") or ""
    if len(abstract) > 200:
        n_abstract_long += 1
    if not XML_TAG_LEAK.search(abstract):
        n_abstract_no_xml_leak += 1
    else:
        issues.append("abstract contains XML-tag-shaped leakage")

    if r.get("authors"):
        n_authors_non_empty += 1
    if r.get("journal"):
        n_journal_ok += 1

    year = r.get("year")
    if isinstance(year, int) and 1990 <= year <= THIS_YEAR + 1:
        n_year_ok += 1
    else:
        issues.append(f"year out of range: {year!r}")

    if r.get("pub_types"):
        n_pubtypes_ok += 1
    else:
        issues.append("pub_types empty")

    if issues:
        per_record_issues.append({"pmid": r.get("pmid"), "issues": issues})

n = len(records)
script_checks.update({
    "all_records_have_required_fields": n_fields_present == n,
    "all_titles_substantive": n_title_ok == n,
    "no_xml_tag_leakage_in_abstracts": n_abstract_no_xml_leak == n,
    "most_abstracts_full_length":
        (n_abstract_long / n) >= 0.6 if n else True,
    "most_records_have_authors":
        (n_authors_non_empty / n) >= 0.9 if n else True,
    "all_journals_named": n_journal_ok == n,
    "all_years_in_range": n_year_ok == n,
    "all_records_have_pub_types": n_pubtypes_ok == n,
})


# ---- report ----
print("Script checks:")
for k, v in script_checks.items():
    print(f"  {'OK' if v else 'FAIL'}  {k}")
if per_record_issues:
    print(f"Per-record issues ({len(per_record_issues)} records):")
    for it in per_record_issues[:5]:
        print(f"  {it['pmid']}: {'; '.join(it['issues'])}")
    if len(per_record_issues) > 5:
        print(f"  …and {len(per_record_issues) - 5} more")

out = f"{STAGE}/eval/eval_script.json"
with open(out, "w") as f:
    json.dump({
        "script": script_checks,
        "per_record_issues": per_record_issues,
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


n_total = len(script_checks)
n_passed = sum(1 for v in script_checks.values() if v)
write_score(STAGE, "script", n_passed, n_total)

assert all(script_checks.values()), \
    "Stage 1 script eval failed — see Per-record issues above"
