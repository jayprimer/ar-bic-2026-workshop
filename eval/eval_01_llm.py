"""Eval for Stage 1 — AI T/F formality check on top-10 records.

Stage 1's job is to capture PubMed metadata cleanly. Screening for
relevance happens in Stage 2 — this eval deliberately stays out of
that. The two T/F questions per record ask only whether the
*captured field looks like well-formed PubMed metadata*, regardless
of whether the paper is on-topic:

  Q1 (title):    Does the title look like a properly formed PubMed
                 article title — complete (not cut off mid-word /
                 mid-phrase), readable, free of garbled or
                 placeholder content?
  Q2 (abstract): Does the abstract look like properly formed PubMed
                 abstract text — complete (not cut off mid-sentence
                 or marked with '...' / '[truncated]'), readable as
                 scientific prose, free of obvious encoding or
                 parsing artifacts?

TRUE means the field is well-formed; FALSE flags an upstream
truncation or parsing artifact. The script check
`no_xml_tag_leakage_in_abstracts` in eval_01_script.py catches one
specific failure mode (inline XML children dropped by `.text`); this
LLM check catches the broader *semantic* version (clipped abstracts,
dangling words, garbled encoding) where a length-floor or regex
guard wouldn't help.

Writes stage_01/eval_llm.json. Companion to eval_01_script.py, which
runs the script checks. Either can run on its own.

Default grader is the same `gpt-5.4-nano` the screener uses; set
EVAL_MODEL to swap for a real cross-model check.
"""
import json
import os

assert os.environ.get("OPENAI_API_KEY"), "eval needs OPENAI_API_KEY"
from openai import OpenAI

MODEL = os.environ.get("EVAL_MODEL", "gpt-5.4-nano")
client = OpenAI()
print(f"AI grader: {MODEL}")

STAGE = "stage_01"
os.makedirs(f"{STAGE}/eval", exist_ok=True)


def grade(question, context):
    """Ask the LLM a strict TRUE/FALSE question grounded in context."""
    prompt = (
        "Answer with strictly TRUE or FALSE based only on the context. "
        "No scoring, no 'partial', no hedging, no explanation. "
        'Return JSON: {"answer": "TRUE" | "FALSE"}.\n\n'
        f"QUESTION:\n{question}\n\nCONTEXT:\n{context}"
    )
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    d = json.loads(resp.choices[0].message.content)
    return d.get("answer", "").upper() == "TRUE"


with open(f"{STAGE}/data/pmids.json") as f:
    records = json.load(f).get("records") or []

# Each tuple: (field_name, question). The question is asked against
# the named field only — relevance/topic intentionally not considered.
QUESTIONS = [
    ("title",
     "Does this string look like a properly formed PubMed article "
     "title — complete (not cut off mid-word or mid-phrase), readable, "
     "and free of garbled characters or placeholder content? Answer "
     "TRUE if the formatting is sound, regardless of whether the topic "
     "is on or off any particular research question."),
    ("abstract",
     "Does this string look like properly formed PubMed abstract "
     "text — complete (not cut off mid-sentence or marked with '...' "
     "or '[truncated]'), readable as scientific prose, and free of "
     "obvious encoding or parsing artifacts? An empty abstract is "
     "FALSE; a short but coherently concluded abstract is TRUE. "
     "Topic relevance is irrelevant to this check."),
]

top = records[:10]
items = []
for rec in top:
    checks = []
    for field, question in QUESTIONS:
        value = rec.get(field, "") or ""
        ctx = f"FIELD: {field}\nVALUE:\n{value}"
        checks.append({
            "field": field, "q": question,
            "answer": grade(question, ctx),
        })
    items.append({"pmid": rec.get("pmid"), "checks": checks})

out = f"{STAGE}/eval/eval_llm.json"
with open(out, "w") as f:
    json.dump({"ai": items}, f, indent=2)

trues = sum(1 for it in items for c in it["checks"] if c["answer"])
total = sum(len(it["checks"]) for it in items)
print(f"AI T/F: {trues}/{total} TRUE across top-{len(top)} records "
      f"× {len(QUESTIONS)} formality questions (title, abstract)")
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


write_score(STAGE, "llm", trues, total)
