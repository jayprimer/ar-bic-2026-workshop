"""Eval for Stage 5 — dynamic AI rubric on one fulltext extraction.

Two-stage LLM eval:
  1. Generate — ask the model to produce N TRUE/FALSE questions
     tailored to the extracted record, each paired with the answer
     that *should* be correct IF the extraction is faithful to the
     paper. Questions are self-contained (encode the claim).
  2. Verify — re-ask the model to answer each question from the
     paper text alone (the grader does NOT see the extracted record
     or the expected answer, so its judgment is independent).

Pass on a question = (grader's actual answer == generator's
expected answer). The final score is the count of passes.

Runs on the first N_PAPERS fulltext extractions in stage_05/data/
(default 2; workshop attendees can edit the constants to scale up or
down). The point is the *pattern* — LLM-generated rubric + grounded
T/F verification — not exhaustive grading.

Both generator and grader default to gpt-5.4-mini. Mini-on-mini
catches more real extraction misses than mini-on-nano (which left
NAM-coverage gaps and bundled-question false negatives across
paragraphs). Workshop attendees can drop the grader to nano via
EVAL_MODEL=gpt-5.4-nano for a cheaper but noisier run, or push
the generator to gpt-5.4 via EVAL_GEN_MODEL for stricter rubrics.
"""
import glob
import json
import os

assert os.environ.get("OPENAI_API_KEY"), "eval needs OPENAI_API_KEY"
from openai import OpenAI

MODEL = os.environ.get("EVAL_MODEL", "gpt-5.4-mini")
GEN_MODEL = os.environ.get("EVAL_GEN_MODEL", "gpt-5.4-mini")
client = OpenAI()
print(f"Generator: {GEN_MODEL}  |  Grader: {MODEL}")

STAGE = "stage_05"
IN_STAGE = "stage_04"
os.makedirs(f"{STAGE}/eval", exist_ok=True)
SKIP = {"eval.json", "eval_script.json", "eval_llm.json", "score.json"}
N_QUESTIONS = 10
N_PAPERS = 2


def llm_json(prompt, model):
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


def generate_questions(rec, n):
    """Ask the LLM to generate {question, expected_answer} pairs.

    The question is what the grader will see (paper text only).
    The expected_answer is what the grader SHOULD say IF the
    extraction is correct — the generator declares this based on
    the extracted record, the grader answers independently."""
    prompt = (
        f"You are designing a quality-check for a structured data "
        f"extraction from a research paper on monoclonal antibody "
        f"animal studies. The JSON record below was produced by "
        f"another LLM from the paper text.\n\n"
        f"Generate exactly {n} TRUE/FALSE checks. For each check, "
        f"return a self-contained question answerable from the paper "
        f"text alone, AND the expected answer (TRUE or FALSE) IF the "
        f"extraction is correct. The grader will not "
        f"see the extracted record or your expected answer — it will "
        f"judge from the paper text alone, and the check passes "
        f"when `grader_answer == expected`.\n\n"
        f"Focus on failure modes that matter for this domain:\n"
        f"  - hallucinated mab_name / target / format\n"
        f"  - misclassified species or study_type in animal_arms\n"
        f"  - wrong n_animals or duration_days\n"
        f"  - concurrent_nam that wasn't actually a NAM in this study\n"
        f"  - threeRs_mentioned over-claim (boilerplate vs methodology)\n"
        f"  - infidelity in author_reduction_recommendation paraphrase\n\n"
        f"Examples (notice expected answer varies):\n"
        f"  Extraction says mab_name=CSL305:\n"
        f'    q: "Does the paper refer to the antibody as CSL305?"\n'
        f'    expected: "TRUE"\n'
        f"  Extraction says threeRs_mentioned=false:\n"
        f'    q: "Does the paper make a methodological 3Rs / NAM / '
        f'reduce-replace-refine statement (beyond boilerplate '
        f'animal-welfare language)?"\n'
        f'    expected: "FALSE"\n\n'
        f"Each question must be SPECIFIC (one claim per question, not "
        f"multi-part).\n\n"
        f'Return strict JSON: {{"items": [{{"q": "...", '
        f'"expected": "TRUE"|"FALSE"}}, ...]}}. No markdown fences, '
        f"no explanation.\n\n"
        f"EXTRACTED RECORD:\n{json.dumps(rec, indent=2)}"
    )
    out = llm_json(prompt, GEN_MODEL)
    return out.get("items", [])


def grade(question, paper_text):
    """Answer a self-contained T/F question against the paper text only."""
    prompt = (
        "Answer with strictly TRUE or FALSE based only on the paper text. "
        "No scoring, no 'partial', no hedging, no explanation. "
        'Return JSON: {"answer": "TRUE" | "FALSE"}.\n\n'
        f"QUESTION:\n{question}\n\nPAPER TEXT:\n{paper_text}"
    )
    d = llm_json(prompt, MODEL)
    return d.get("answer", "").upper() == "TRUE"


# ---- pick the first N_PAPERS fulltext extractions ----
targets = []
for jpath in sorted(glob.glob(f"{STAGE}/data/*.json")):
    if os.path.basename(jpath) in SKIP:
        continue
    with open(jpath) as f:
        rec = json.load(f)
    if rec.get("source_type") == "fulltext":
        targets.append((jpath, rec))
        if len(targets) >= N_PAPERS:
            break
assert targets, "no fulltext extractions in stage_05/data/ — nothing to grade"
print(f"Grading {len(targets)} fulltext paper(s)")

per_paper = []
for jpath, rec in targets:
    stem = os.path.splitext(os.path.basename(jpath))[0]
    txt_path = f"{IN_STAGE}/data/{stem}.md"
    with open(txt_path) as f:
        paper_text = f.read()
    print(f"\n=== {stem} (pmid={rec.get('pmid')}, {len(paper_text):,} chars) ===")

    items = generate_questions(rec, N_QUESTIONS)
    print(f"Generated {len(items)} questions")

    checks = []
    for it in items:
        q = it.get("q", "")
        expected = (it.get("expected") or "").upper() == "TRUE"
        actual = grade(q, paper_text)
        is_pass = actual == expected
        print(f"  expected={'T' if expected else 'F'} "
              f"actual={'T' if actual else 'F'}  "
              f"{'PASS' if is_pass else 'FAIL'}  {q}")
        checks.append({"q": q, "expected": expected,
                       "actual": actual, "pass": is_pass})
    n_pass = sum(1 for c in checks if c["pass"])
    print(f"  → {n_pass}/{len(checks)} PASS")
    per_paper.append({"stem": stem, "pmid": rec.get("pmid"),
                      "source_type": rec.get("source_type"),
                      "checks": checks})

out = f"{STAGE}/eval/eval_llm.json"
with open(out, "w") as f:
    json.dump({"ai_per_paper": per_paper}, f, indent=2)
print(f"\nWrote {out}")


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


all_checks = [c for it in per_paper for c in it["checks"]]
passed = sum(1 for c in all_checks if c["pass"])
write_score(STAGE, "llm", passed, len(all_checks))
