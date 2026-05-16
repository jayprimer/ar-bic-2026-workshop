"""Eval for Stage 2 — criteria-decomposition AI rubric.

For each sampled record (5 included + 5 excluded, seed=42):

  1. Generate — ask the model to produce N TRUE/FALSE questions, each
     targeting ONE specific criterion that is load-bearing for this
     abstract. Each question is tagged with:
       category = "include"  → TRUE answer = inclusion criterion met
       category = "exclude"  → TRUE answer = exclusion criterion triggered
     The generator sees CRITERIA + ABSTRACT only — NOT the verdict —
     so the choice of criteria is independent of the screen outcome.
  2. Verify — grader answers each question from CRITERIA + ABSTRACT
     alone (independent judgment).
  3. Infer the verdict from the answers:
       inferred = "exclude" if any exclude-category answer is TRUE
                            OR any include-category answer is FALSE
                  else      "include"
  4. Pass on the record = (inferred == screener's verdict).

No "should this be included?" meta-question — the verdict is
computed from the criterion-by-criterion decomposition. Score is
records-passed / records-sampled.

EVAL_GEN_MODEL controls the generator (defaults to gpt-5.4-mini —
picking the load-bearing criteria and tagging polarity correctly
needs the smarter model). EVAL_MODEL controls the grader
(defaults to gpt-5.4-nano — N grade calls per record dominate
cost; nano keeps it cheap). Override either via env.
"""
import json
import os
import random

assert os.environ.get("OPENAI_API_KEY"), "eval needs OPENAI_API_KEY"
from openai import OpenAI

MODEL = os.environ.get("EVAL_MODEL", "gpt-5.4-nano")
GEN_MODEL = os.environ.get("EVAL_GEN_MODEL", "gpt-5.4-mini")
client = OpenAI()
print(f"Generator: {GEN_MODEL}  |  Grader: {MODEL}")

STAGE = "stage_02"
os.makedirs(f"{STAGE}/eval", exist_ok=True)
N_QUESTIONS = 5   # mix of include- and exclude-category criteria


def load_config(path):
    """Parse KEY = value with '#' comments and indented continuation lines."""
    cfg, last_key = {}, None
    with open(path) as f:
        for raw in f:
            line = raw.rstrip("\n")
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if line[:1].isspace() and last_key is not None:
                cfg[last_key] = (cfg[last_key] + " " + stripped).strip()
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                last_key = k.strip()
                cfg[last_key] = v.strip()
    return cfg


cfg = load_config(f"{STAGE}/input.txt")
CRITERIA_FILE = cfg.get("CRITERIA_FILE", f"{STAGE}/criteria.txt")

with open(f"{STAGE}/data/screened.json") as f:
    recs = json.load(f)
with open(CRITERIA_FILE) as f:
    CRITERIA = f.read()


def llm_json(prompt, model):
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


def generate_questions(rec, n):
    """Generator sees CRITERIA + ABSTRACT only (no verdict, no
    rationale). Returns {q, category} pairs; category is "include"
    or "exclude" per the rules in the module docstring."""
    prompt = (
        f"You are designing a quality-check for a literature-screening "
        f"decision. The criteria below define which papers belong in a "
        f"systematic review of mAb animal studies.\n\n"
        f"Read the CRITERIA carefully, then read the ABSTRACT. Generate "
        f"{n} self-contained TRUE/FALSE questions, each targeting ONE "
        f"specific criterion from the CRITERIA text. Mix include- and "
        f"exclude-side criteria; aim for ~half of each.\n\n"
        f"Each question carries a category:\n"
        f'  "include": a TRUE answer means an INCLUSION criterion is '
        f"satisfied. Examples:\n"
        f'    - "Is this a primary research study?"  (TRUE = included)\n'
        f'    - "Does the abstract describe an in-vivo mammalian study '
        f'arm?"  (TRUE = included)\n'
        f'    - "Is the species an eligible mammal (mouse/rat/cyno/'
        f'rhesus/dog/rabbit/minipig)?"  (TRUE = included)\n'
        f'  "exclude": a TRUE answer means an EXCLUSION criterion fires. '
        f"Examples:\n"
        f'    - "Is this a review, meta-analysis, perspective, or '
        f'commentary?"  (TRUE = excluded)\n'
        f'    - "Is the work in-vitro / cell-line only with no in-vivo '
        f'arm?"  (TRUE = excluded)\n'
        f'    - "Is this a veterinary study (animal as patient, not as '
        f'preclinical model)?"  (TRUE = excluded)\n'
        f'    - "Is the mAb-conjugate (radioligand, toxin) the primary '
        f'subject?"  (TRUE = excluded)\n\n'
        f"CRITICAL — POLARITY RULE: when phrasing a question, ask "
        f"yourself \"what does a TRUE answer mean for the verdict?\". "
        f"If TRUE points toward INCLUSION, the category is \"include\". "
        f"If TRUE points toward EXCLUSION, the category is \"exclude\".\n\n"
        f"FORBIDDEN PHRASING: never use \"rather than\", \"as opposed "
        f"to\", or \"is X the case (rather than Y)\". They confuse "
        f"polarity. Example of the BAD pattern and how to fix it:\n"
        f"  BAD  (tag=exclude): \"Is the paper focused on in-vivo PK "
        f"rather than a review or in-vitro study?\"  ← TRUE here "
        f"actually means INCLUDE, so the exclude tag is wrong.\n"
        f"  GOOD (tag=include): \"Does the abstract describe an in-vivo "
        f"PK study?\"  ← TRUE clearly means inclusion-supportive.\n"
        f"  GOOD (tag=exclude): \"Is this a review or meta-analysis?\""
        f"  ← TRUE clearly means exclusion-triggering.\n\n"
        f"Frame each question as a single, clear positive assertion. "
        f"Do not bundle multiple conjunctions (\"primary research AND "
        f"in-vivo AND eligible species AND supporting development\") "
        f"into one question — that creates ambiguous FALSE answers.\n\n"
        f"REQUIREMENTS:\n"
        f"  - Each question must be self-contained — answerable from "
        f"CRITERIA + ABSTRACT alone, no outside knowledge.\n"
        f"  - One concrete claim per question (no multi-part questions).\n"
        f"  - For exclude-category questions, if the abstract is "
        f"ambiguous about which exclusion criterion might apply, cover "
        f"more than one of {{review, in-vitro only, veterinary, "
        f"xenograft-efficacy only, conjugate-primary, case-report}}.\n\n"
        f'Return strict JSON: {{"items": [{{"q": "...", '
        f'"category": "include"|"exclude"}}, ...]}}. No markdown '
        f"fences, no explanation.\n\n"
        f"CRITERIA:\n{CRITERIA}\n\n"
        f"ABSTRACT:\nPMID: {rec['pmid']}\nTitle: {rec['title']}\n"
        f"Abstract: {rec['abstract']}"
    )
    return llm_json(prompt, GEN_MODEL).get("items", [])


def grade(question, rec):
    """Answer T/F from CRITERIA + ABSTRACT only. Grader never sees
    the verdict or the question's category."""
    ctx = (
        f"CRITERIA:\n{CRITERIA}\n\n"
        f"ABSTRACT:\nPMID: {rec['pmid']}\nTitle: {rec['title']}\n"
        f"Abstract: {rec['abstract']}"
    )
    prompt = (
        "Answer with strictly TRUE or FALSE based only on the context. "
        "No scoring, no 'partial', no hedging, no explanation. "
        'Return JSON: {"answer": "TRUE" | "FALSE"}.\n\n'
        f"QUESTION:\n{question}\n\nCONTEXT:\n{ctx}"
    )
    return llm_json(prompt, MODEL).get("answer", "").upper() == "TRUE"


def infer_verdict(checks):
    """exclude if any exclude-category answer is TRUE OR any
    include-category answer is FALSE; else include."""
    any_exclude_triggered = any(
        c["actual"] for c in checks if c["category"] == "exclude"
    )
    any_include_missing = any(
        not c["actual"] for c in checks if c["category"] == "include"
    )
    return "exclude" if (any_exclude_triggered or any_include_missing) else "include"


# ---- balanced sample ----
rng = random.Random(42)
includes = [r for r in recs if r.get("verdict") == "include"]
excludes = [r for r in recs if r.get("verdict") == "exclude"]
inc_sample = rng.sample(includes, min(5, len(includes)))
exc_sample = rng.sample(excludes, min(5, len(excludes)))
sample = inc_sample + exc_sample
print(f"Sampled {len(inc_sample)} include + {len(exc_sample)} exclude")


# ---- generate + verify per record ----
items = []
for rec in sample:
    qcat = generate_questions(rec, N_QUESTIONS)
    checks = []
    for ix in qcat:
        q = ix.get("q", "")
        cat = ix.get("category", "include")
        actual = grade(q, rec)
        checks.append({"q": q, "category": cat, "actual": actual})
    inferred = infer_verdict(checks)
    is_pass = inferred == rec["verdict"]
    inc_t = sum(1 for c in checks if c["category"] == "include" and c["actual"])
    inc_f = sum(1 for c in checks if c["category"] == "include" and not c["actual"])
    exc_t = sum(1 for c in checks if c["category"] == "exclude" and c["actual"])
    exc_f = sum(1 for c in checks if c["category"] == "exclude" and not c["actual"])
    print(f"  {rec['pmid']} ({rec['verdict']} → {inferred})  "
          f"{'PASS' if is_pass else 'FAIL'}  "
          f"[inc T/F={inc_t}/{inc_f}, exc T/F={exc_t}/{exc_f}]")
    items.append({"pmid": rec["pmid"], "verdict": rec["verdict"],
                  "inferred": inferred, "pass": is_pass,
                  "checks": checks})

out = f"{STAGE}/eval/eval_llm.json"
with open(out, "w") as f:
    json.dump({"ai_per_record": items}, f, indent=2)
print(f"Wrote {out}")


def write_score(stage, key, passed, total):
    """Merge {passed, total, percent} under `key` into stage/eval/score.json."""
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


passed = sum(1 for it in items if it["pass"])
write_score(STAGE, "llm", passed, len(items))
