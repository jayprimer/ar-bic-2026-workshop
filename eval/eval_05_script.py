"""Eval for Stage 5 — script checks only (no API key needed).

Deterministic schema-shape checks on stage_05/*.json:
  - required top-level keys (pmid populated, animal_arms a list)
  - every enum-valued field is in its declared vocabulary
  - n_animals and duration_days are non-negative integers where present

Writes stage_05/eval_script.json and merges a `script` block into
stage_05/score.json. Companion to eval_05_llm.py.
"""
import glob
import json
import os

STAGE = "stage_05"
os.makedirs(f"{STAGE}/eval", exist_ok=True)

ENUM_SOURCE = {"fulltext", "abstract-only"}
ENUM_FORMAT = {"IgG1", "IgG2", "IgG3", "IgG4", "bispecific", "ADC",
               "Fab", "Fc-fusion", "other"}
ENUM_STAGE = {"discovery", "lead optimization", "IND-enabling",
              "clinical translation", "post-approval"}
ENUM_REG = {"none-stated", "IND-supporting", "BLA-supporting",
            "post-marketing"}
ENUM_SPECIES = {"mouse", "rat", "cynomolgus", "rhesus", "dog", "rabbit",
                "minipig", "other"}
ENUM_STUDY = {"PK", "single-dose tox", "repeat-dose tox", "immunogenicity",
              "biodistribution", "efficacy", "TCR"}
ENUM_JUSTIF = {"pharmacological relevance", "regulatory expectation",
               "historical precedent", "not stated"}
ENUM_CR = {"in-vitro binding shown", "sequence homology only",
           "not addressed"}

SKIP = {"eval.json", "eval_script.json", "eval_llm.json", "score.json"}


script_per_paper = []
for jpath in sorted(glob.glob(f"{STAGE}/data/*.json")):
    if os.path.basename(jpath) in SKIP:
        continue
    stem = os.path.splitext(os.path.basename(jpath))[0]
    with open(jpath) as f:
        rec = json.load(f)
    arms = rec.get("animal_arms") or []
    enums_clean = True
    if rec.get("format") not in ENUM_FORMAT | {None}:
        enums_clean = False
    if rec.get("development_stage") not in ENUM_STAGE | {None}:
        enums_clean = False
    if rec.get("regulatory_context") not in ENUM_REG | {None}:
        enums_clean = False
    for arm in arms:
        if arm.get("species") not in ENUM_SPECIES | {None}:
            enums_clean = False
        if arm.get("study_type") not in ENUM_STUDY | {None}:
            enums_clean = False
        if arm.get("species_justification") not in ENUM_JUSTIF | {None}:
            enums_clean = False
        if arm.get("cross_reactivity_evidence") not in ENUM_CR | {None}:
            enums_clean = False
    numerics_clean = all(
        (arm.get("n_animals") is None or
         (isinstance(arm.get("n_animals"), int) and arm["n_animals"] >= 0))
        and (arm.get("duration_days") is None or
             (isinstance(arm.get("duration_days"), int)
              and arm["duration_days"] >= 0))
        for arm in arms
    )
    script_per_paper.append({
        "stem": stem,
        "pmid": rec.get("pmid"),
        "has_required_keys": bool(rec.get("pmid")) and isinstance(arms, list),
        "source_type_valid": rec.get("source_type") in ENUM_SOURCE,
        "enums_within_vocab": enums_clean,
        "numerics_non_negative": numerics_clean,
    })

print("Script checks (per paper):")
for p in script_per_paper:
    flags = "".join(
        "OK " if v else "FAIL " for v in
        [p["has_required_keys"], p["source_type_valid"],
         p["enums_within_vocab"], p["numerics_non_negative"]]
    )
    print(f"  {p['stem']}: keys/source/enums/numerics  {flags}")

script_pass = all(
    p["has_required_keys"] and p["source_type_valid"]
    and p["enums_within_vocab"] and p["numerics_non_negative"]
    for p in script_per_paper
)

out = f"{STAGE}/eval/eval_script.json"
with open(out, "w") as f:
    json.dump({"script_per_paper": script_per_paper}, f, indent=2)
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


SCRIPT_KEYS = ("has_required_keys", "source_type_valid",
               "enums_within_vocab", "numerics_non_negative")
passed = sum(1 for p in script_per_paper for k in SCRIPT_KEYS if p[k])
total  = len(script_per_paper) * len(SCRIPT_KEYS)
write_score(STAGE, "script", passed, total)

assert script_pass, "Stage 5 script eval failed (see per-paper flags above)"
