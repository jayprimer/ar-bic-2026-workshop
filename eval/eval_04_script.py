"""Eval for Stage 4 — PDF / XML → text.

SCRIPT-only. Every converted file is large enough (already asserted
in 04_pdf_to_text.py) AND the abstract's opening 80 characters from
screened.json round-trip into the converted text. That's the cheapest
check that the source actually got converted to readable prose.

Writes stage_04/eval_script.json; prints round-trip pass/fail.
"""
import json
import os
import re

STAGE = "stage_04"
os.makedirs(f"{STAGE}/eval", exist_ok=True)

with open("stage_03/data/fetched.json") as f:
    fetched = json.load(f)
with open("stage_02/data/screened.json") as f:
    abstract_by_pmid = {r["pmid"]: r["abstract"] for r in json.load(f)}


def first_words(s, n=80):
    s = re.sub(r"\s+", " ", (s or "")).strip()
    return s[:n]


def alnum(s):
    """Lowercase, then drop everything except [a-z0-9]. Erases the
    en-dash / soft-hyphen / smart-quote variants that publishers
    introduce between PubMed metadata and the rendered PDF."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


# ---- script checks ----
# Stage 4 now converts every screen-included PMID — fulltext (.pdf/.xml)
# AND metadata-only (.json) fallbacks. The size floor differs by source
# type because abstract-only output is intrinsically smaller than
# parsed fulltext.
def _floor(path):
    return 500 if path.endswith(".json") else 5_000


errors = []
items = []
for pmid, path in fetched.items():
    if not path:
        continue
    stem = os.path.splitext(os.path.basename(path))[0]
    text_path = f"{STAGE}/data/{stem}.md"
    if not os.path.exists(text_path):
        errors.append(f"{pmid} ({stem}): text file missing")
        items.append({"pmid": pmid, "stem": stem,
                      "size_ok": False, "abstract_roundtrip": False})
        continue
    floor = _floor(path)
    size_ok = os.path.getsize(text_path) > floor
    with open(text_path) as f:
        text = f.read()
    needle = first_words(abstract_by_pmid.get(pmid, ""))
    rt = bool(needle) and alnum(needle) in alnum(text)
    items.append({
        "pmid": pmid, "stem": stem,
        "size_ok": size_ok, "abstract_roundtrip": rt,
        "needle": needle,
    })
    if not size_ok:
        errors.append(f"{pmid} ({stem}): converted text < {floor}B")
    if not rt and needle:
        errors.append(f"{pmid} ({stem}): abstract first sentence does not round-trip")

n_files = len(items)
n_size_ok = sum(1 for it in items if it["size_ok"])
n_rt = sum(1 for it in items if it["abstract_roundtrip"])

script_checks = {
    "every_screened_paper_has_text": all(
        os.path.exists(f"{STAGE}/data/{os.path.splitext(os.path.basename(p))[0]}.md")
        for p in fetched.values() if p
    ),
    "all_files_above_size_floor": n_size_ok == n_files,
    "all_abstracts_round_trip": n_rt == n_files,
}

print("Script checks:")
for k, v in script_checks.items():
    print(f"  {'OK' if v else 'FAIL'}  {k}")
if errors:
    print("Errors:")
    for e in errors:
        print(f"    {e}")
assert script_checks["every_screened_paper_has_text"], "Stage 4 script eval failed"

out = f"{STAGE}/eval/eval_script.json"
with open(out, "w") as f:
    json.dump({"script": script_checks, "items": items}, f, indent=2)

print(f"Round-trip: {n_rt}/{n_files} abstract prefixes match converted text (alphanumeric)")
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
