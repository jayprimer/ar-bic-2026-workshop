"""Generate workshop .ipynb notebooks. Idempotent — re-runnable."""
import json
import os

REPO = "jayprimer/ar-bic-2026-workshop"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NB_DIR = os.path.join(ROOT, "notebooks")
os.makedirs(NB_DIR, exist_ok=True)


def md(text):
    return {"cell_type": "markdown", "metadata": {},
            "source": [l + "\n" for l in text.rstrip("\n").split("\n")]}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [],
            "source": [l + "\n" for l in text.rstrip("\n").split("\n")]}


def notebook(cells):
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3",
                           "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
            "colab": {"provenance": []},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def write(name, cells):
    path = os.path.join(NB_DIR, name)
    with open(path, "w") as f:
        json.dump(notebook(cells), f, indent=1)
    print(f"wrote {path}")


# ---- common cells -------------------------------------------------------

BOOTSTRAP = code(f"""\
# Bootstrap: clone the workshop repo into /content and cd into it.
# Idempotent — safe to re-run.
import os, subprocess, sys
REPO_DIR = "/content/ar-bic-2026-workshop"
if not os.path.exists(REPO_DIR):
    subprocess.run(
        ["git", "clone", "--depth", "1",
         "https://github.com/{REPO}.git", REPO_DIR],
        check=True,
    )
os.chdir(REPO_DIR)
print("cwd:", os.getcwd())""")

KEY_BRIDGE = code("""\
# OpenAI key bridge: Colab's userdata.get() does NOT populate os.environ,
# but our scripts read os.environ["OPENAI_API_KEY"]. Bridge it once.
# Add the key in Colab via the left sidebar → "Secrets" (key icon) → name it OPENAI_API_KEY.
import os
try:
    from google.colab import userdata
    key = userdata.get("OPENAI_API_KEY")
    if key:
        os.environ["OPENAI_API_KEY"] = key
        print("OPENAI_API_KEY set in os.environ")
    else:
        print("WARNING: OPENAI_API_KEY secret is empty — Stage 2/5 and *_llm.py evals will fail")
except Exception as e:
    print("Not running in Colab or userdata unavailable; set OPENAI_API_KEY yourself.")
    print("Detail:", e)""")

DEPS = code("""\
# Install dependencies. Idempotent (pip skips already-installed; npm re-link is cheap).
# liteparse only matters for Stage 4 but installing it everywhere keeps each
# notebook self-contained, which is the whole point of re-running this cell.
!pip install -q -r requirements.txt
!npm install -g @llamaindex/liteparse 2>&1 | tail -3""")

STAGE_CONFIGS = code("""\
# Copy bundle-shipped configs into the directories each stage script expects.
# Each stage's input.txt / criteria.txt / schema.json lives under configs/
# in the repo; the actual scripts read them relative to cwd.
import os, shutil
os.makedirs("stage_01", exist_ok=True)
os.makedirs("stage_02", exist_ok=True)
shutil.copy("configs/stage_01_input.txt",    "stage_01/input.txt")
shutil.copy("configs/stage_02_input.txt",    "stage_02/input.txt")
shutil.copy("configs/stage_02_criteria.txt", "stage_02/criteria.txt")
shutil.copy("configs/schema.json",           "schema.json")
print("configs staged")""")


def load_prior_outputs_cell(stage_num):
    """Cell that copies reference_outputs for all stages BEFORE stage_num.

    A participant who opens stage_N directly in a fresh Colab runtime needs
    stages 1..N-1's outputs on disk so this stage has inputs to work with.
    The canonical reference run is used; if the participant later re-does
    an earlier stage in this same runtime, their output will overwrite the
    reference.
    """
    if stage_num <= 1:
        return None
    return code(f"""\
# Load prior stages' reference outputs as inputs for Stage {stage_num}.
# Each Colab notebook opens with a fresh runtime, so any work done in a
# Stage <{stage_num} notebook in a DIFFERENT runtime is not visible here.
# This cell makes the stage runnable in isolation against the canonical
# reference run. If you re-run an earlier stage IN THIS runtime, your
# output replaces these reference files (cwd is /content/...).
import os, shutil, glob
for n in range(1, {stage_num}):
    dst = f"stage_0{{n}}/data"
    src = f"reference_outputs/stage_0{{n}}/data"
    if not os.path.isdir(src):
        continue
    os.makedirs(dst, exist_ok=True)
    # Only seed if the participant hasn't produced anything for this stage
    # in the current runtime — otherwise we'd clobber their work.
    if any(os.scandir(dst)):
        print(f"skip stage_0{{n}} — already has files (keeping your work)")
        continue
    for src_file in glob.glob(f"{{src}}/*"):
        shutil.copy(src_file, dst)
    print(f"seeded stage_0{{n}}/data from reference_outputs")""")


# ---- Stage 0: setup -----------------------------------------------------

stage0 = [
    md("""\
# Stage 0 — Setup

One-time setup for the workshop. Run every cell top-to-bottom.

You'll install Python + Node dependencies, bridge your OpenAI key into
the environment, and stage the bundle-shipped config files into the
working directories each stage expects.
"""),

    md("## 1. Clone the repo"),
    BOOTSTRAP,

    md("## 2. Install dependencies\n\n"
       "Python: `openai`. Node: `@llamaindex/liteparse` (Stage 4's PDF→text CLI)."),
    code("!pip install -q -r requirements.txt"),
    code("# liteparse is a Node CLI, not a Python lib. Stage 4 invokes it via subprocess.\n"
         "!npm install -g @llamaindex/liteparse 2>&1 | tail -5\n"
         "!lit --version || echo 'lit not on PATH — check the install output above'"),

    md("## 3. Bridge your OpenAI key\n\n"
       "Add `OPENAI_API_KEY` in **Colab Secrets** (key icon in the left sidebar) "
       "and toggle notebook access, then run this cell."),
    KEY_BRIDGE,

    md("## 4. Stage the config files\n\n"
       "Each stage script reads `stage_NN/input.txt` (and `stage_02/criteria.txt`) "
       "relative to the current working directory. Copy the bundle-shipped configs "
       "into place so participant scripts find them."),
    code("""\
import os, shutil
os.makedirs("stage_01", exist_ok=True)
os.makedirs("stage_02", exist_ok=True)
shutil.copy("configs/stage_01_input.txt",    "stage_01/input.txt")
shutil.copy("configs/stage_02_input.txt",    "stage_02/input.txt")
shutil.copy("configs/stage_02_criteria.txt", "stage_02/criteria.txt")
# Stage 5 reads schema.json from cwd, so put a copy at the repo root too.
shutil.copy("configs/schema.json", "schema.json")
print("staged:", os.listdir("stage_01"), os.listdir("stage_02"))"""),

    md("""\
## 5. You're ready

Open `notebooks/stage_01_search.ipynb` next.

If anything failed above, re-run the failing cell — most install hiccups
clear on retry. Network errors hitting NCBI later in the workshop are
also retry-friendly.
"""),
]
write("stage_00_setup.ipynb", stage0)


# ---- per-stage scaffolding ----------------------------------------------

def stage_notebook(num, name, spec, gotchas, seed,
                   inspect_output, eval_inline, skip_copy,
                   inputs_cell=None, inputs_intro="",
                   implementation_starter=None, fallback_post=""):
    """Generate one stage notebook.

    inputs_cell      — code string defining this stage's inputs as Python
                       variables. Should also persist any expected files
                       to disk so the standalone eval scripts under eval/
                       still work. Pass None for stages with no user-
                       configurable inputs.
    inspect_output   — code string that displays the stage's output
                       inline (e.g., as a pandas DataFrame or pretty
                       JSON). This replaces the old assert-only verify.
    eval_inline      — code string with the full eval logic inlined.
                       Should print PASS/FAIL summary and write
                       stage_NN/eval/{eval_script.json, score.json}.
    """
    section = 0
    def heading(title):
        nonlocal section
        section += 1
        return md(f"## {section}. {title}")

    def sub_heading(title):
        return md(f"### {title}")

    cells = [
        md(f"# Stage {num} — {name}\n\n"
           "Re-create this stage's script with Gemini's help. The cells "
           "below give you the spec, the seed, the gotchas, and an "
           "inline eval. The implementation itself is yours to write."),

        heading("Setup"),
        md("Every cell in this section is idempotent and safe to re-run. "
           "If you opened this notebook fresh (without running anything "
           "else in the same runtime), run them top-to-bottom."),

        sub_heading("Clone the repo and `cd` into it"),
        BOOTSTRAP,

        sub_heading("Install dependencies"),
        md("Python (`openai`) and the Node CLI `@llamaindex/liteparse`. "
           "First run takes ~30s; re-runs are near-instant."),
        DEPS,
    ]
    if num in (2, 5):
        cells += [
            sub_heading("Bridge your OpenAI key"),
            md("Add `OPENAI_API_KEY` in Colab's Secrets panel (key icon, "
               "left sidebar) and toggle notebook access first."),
            KEY_BRIDGE,
        ]
    else:
        cells += [
            sub_heading("(no API key needed for this stage)"),
            code("# This stage doesn't call the OpenAI API."),
        ]

    prior = load_prior_outputs_cell(num)
    if prior:
        cells += [
            sub_heading("Seed prior stages' outputs from the reference run"),
            md(f"Stage {num} reads outputs from earlier stages. Each Colab "
               "notebook gets its own runtime, so work done in another "
               "notebook is not visible here. This cell seeds "
               f"`stage_01..stage_{num-1:02d}/data/` from the canonical "
               f"reference run so Stage {num} has inputs to work with — "
               "but only when the dir is empty, so re-running an earlier "
               "stage IN THIS runtime is not clobbered."),
            prior,
        ]

    if inputs_cell is not None:
        cells += [
            heading("Configure inputs"),
            md(inputs_intro or "Edit the variables below — they drive your "
               "implementation. The cell also writes any files the standalone "
               "eval scripts (`eval/*.py`) expect on disk."),
            code(inputs_cell),
        ]

    cells += [
        heading("Spec — paste this into Gemini"),
        md("Open the Gemini side panel in Colab (sparkles icon, top right) "
           "and paste the block below as your prompt. Then iterate.\n\n"
           f"```\n{spec}\n```"),

        heading("Gotchas Gemini probably won't know"),
        md("Copy any that apply into Gemini if it goes off-track:\n\n" + gotchas),

        heading("Seed — a few lines to anchor Gemini"),
        code(seed),

        heading("Your implementation"),
        md("Drive Gemini to fill this in. Iterate until the inspect cell "
           "below shows reasonable output and the eval cell passes."),
        code(implementation_starter or
             f"# TODO: implement Stage {num} here.\n"
             "# Read the spec above. Use the seed cell's imports.\n"
             "# When done, run the inspect + eval cells next.\n"),

        heading("Inspect output"),
        code(inspect_output),

        heading("Run eval"),
        md("Inline eval — same checks as `eval/eval_"
           f"{num:02d}_script.py`, but the code is right here so you can "
           "see what it's measuring. Writes "
           f"`stage_{num:02d}/eval/eval_script.json` + `score.json`."),
        code(eval_inline),
    ]
    if fallback_post:
        cells.append(md(fallback_post))

    cells += [
        heading("Stuck? Skip this stage"),
        md(f"Copy the reference run's Stage {num} output into place so the "
           "next stage's notebook can still run. Use this sparingly — "
           "the point of the workshop is to *re-create* each stage."),
        code(skip_copy),
    ]
    write(f"stage_{num:02d}_{name.lower().replace(' ', '_')}.ipynb", cells)


# ---------- Stage 1 ----------
stage_notebook(
    num=1, name="search",
    inputs_intro="Edit the PubMed search inputs below. The variables in this "
                 "cell drive your implementation directly — your script reads "
                 "them by name, not from a file.",
    inputs_cell="""\
# PubMed search inputs. Edit freely; canonical workshop values shown.
QUERY = (
    '("monoclonal antibody"[Title/Abstract] OR mAb[Title/Abstract]'
    ' OR "monoclonal antibodies"[Title/Abstract])'
    ' AND (pharmacokinetic*[Title/Abstract] OR toxicology[Title/Abstract]'
    ' OR toxicity[Title/Abstract] OR immunogenicity[Title/Abstract]'
    ' OR biodistribution[Title/Abstract])'
    ' AND (cynomolgus[Title/Abstract] OR "non-human primate"[Title/Abstract]'
    ' OR NHP[Title/Abstract] OR mouse[Title/Abstract]'
    ' OR rat[Title/Abstract] OR rodent[Title/Abstract])'
    ' AND ("2025"[Date - Publication] : "2026"[Date - Publication])'
)
N = 30                             # how many PMIDs to fetch (top N by date)
TOOL = "ar-bic-2026-workshop"
EMAIL = "workshop@example.org"

print(f"Query ({len(QUERY)} chars): {QUERY[:120]}...")
print(f"N={N}  TOOL={TOOL!r}  EMAIL={EMAIL!r}")""",
    spec="""\
Write Python that (top-to-bottom in the implementation cell, no
function-with-main wrapper needed):

1. Uses the QUERY, N, TOOL, EMAIL variables from the previous cell.
2. Calls NCBI E-utilities `esearch.fcgi` (db=pubmed, retmax=N,
   retmode=json, sort=date) and assigns the PMID list to a variable
   named `pmids`.
3. Calls NCBI E-utilities `efetch.fcgi` (db=pubmed, retmode=xml) for
   those PMIDs and parses each record into a dict with these keys:
   pmid, title, abstract, authors (list), first_author, journal,
   year (int), pub_types (list). Assign to a variable named
   `records`.
4. Re-sorts `records` to match the esearch `pmids` order (efetch
   ordering is not guaranteed).
5. Asserts: `len(records) == len(pmids)`, and every record has a
   non-empty `pmid` and `title`.

Use only the standard library (urllib, json, xml.etree.ElementTree).
Do NOT use Biopython or `requests`. Do NOT save to disk — the next
cell handles persistence.""",
    gotchas="""\
- **Abstracts are nested XML.** Use `el.itertext()` joined together,
  NOT `el.text`, when reading `<ArticleTitle>` and `<AbstractText>`.
  `.text` silently truncates at the first inline child (`<i>`,
  `<sub>`, `<sup>`).
- **Abstract can be multi-part labeled.** Find all
  `.//Abstract/AbstractText`, read each `Label` attribute, and join
  them as `"BACKGROUND: ... METHODS: ..."`.
- **efetch can reorder.** Re-sort `records` to match the esearch
  `pmids` order before saving.
- **Identify yourself to NCBI.** Pass `tool` and `email` URL params
  (anonymous clients are throttled hard).
""",
    seed="""\
import json, os, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
HEADERS = {"User-Agent": "ar-bic-2026/0.1"}

# Implementation goes in the next cell.
# Produce two variables for the inspect cell to consume:
#   pmids   : list[str]
#   records : list[dict]
""",
    inspect_output="""\
# Save your results to disk for downstream stages + eval, then display.
import json, os
os.makedirs("stage_01/data", exist_ok=True)
with open("stage_01/data/pmids.json", "w") as f:
    json.dump({"query": QUERY, "n_requested": N,
               "pmids": pmids, "records": records}, f, indent=2)
print(f"Saved {len(records)} records → stage_01/data/pmids.json\\n")

print("First 3 records:")
for r in records[:3]:
    print(f"  PMID {r['pmid']}: {r['title'][:78]}")
    print(f"    {r.get('first_author','?')} ({r.get('year','?')}) · "
          f"{(r.get('journal') or '')[:50]}")
    print(f"    Abstract: {(r.get('abstract') or '')[:140]}…\\n")""",
    eval_inline="""\
# Eval — same checks as eval/eval_01_script.py, inlined so you can see
# what's being measured. Reads stage_01/data/pmids.json from disk.
import datetime, json, os, re

XML_TAG_LEAK = re.compile(r"</?[a-zA-Z]")
REQUIRED_FIELDS = {"pmid", "title", "abstract", "authors", "first_author",
                   "journal", "year", "pub_types"}
THIS_YEAR = datetime.date.today().year

os.makedirs("stage_01/eval", exist_ok=True)
with open("stage_01/data/pmids.json") as f:
    doc = json.load(f)
pmids   = doc["pmids"]
records = doc.get("records") or []

# ---- PMID-list shape ----
checks = {
    "pmids_non_empty":   bool(pmids),
    "all_numeric":       all(p.isdigit() for p in pmids),
    "no_duplicates":     len(pmids) == len(set(pmids)),
    "respects_cap":      len(pmids) <= doc.get("n_requested", len(pmids)),
    "records_match_pmids": [r["pmid"] for r in records] == pmids,
}

# ---- per-record completeness ----
n = len(records)
counts = dict(fields=0, title=0, abs_long=0, abs_clean=0,
              authors=0, journal=0, year=0, pub_types=0)
issues = []
for r in records:
    rec_issues = []
    if set(r.keys()) >= REQUIRED_FIELDS: counts["fields"] += 1
    else: rec_issues.append(f"missing keys: {REQUIRED_FIELDS - set(r.keys())}")
    if r.get("title") and len(r["title"]) > 10: counts["title"] += 1
    else: rec_issues.append("title missing or < 10 chars")
    ab = r.get("abstract") or ""
    if len(ab) > 200: counts["abs_long"] += 1
    if not XML_TAG_LEAK.search(ab): counts["abs_clean"] += 1
    else: rec_issues.append("abstract contains XML-tag-shaped leakage")
    if r.get("authors"): counts["authors"] += 1
    if r.get("journal"): counts["journal"] += 1
    yr = r.get("year")
    if isinstance(yr, int) and 1990 <= yr <= THIS_YEAR + 1: counts["year"] += 1
    else: rec_issues.append(f"year out of range: {yr!r}")
    if r.get("pub_types"): counts["pub_types"] += 1
    else: rec_issues.append("pub_types empty")
    if rec_issues: issues.append({"pmid": r.get("pmid"), "issues": rec_issues})

checks.update({
    "all_records_have_required_fields": counts["fields"] == n,
    "all_titles_substantive":           counts["title"] == n,
    "no_xml_tag_leakage_in_abstracts":  counts["abs_clean"] == n,
    "most_abstracts_full_length":       (counts["abs_long"]/n) >= 0.6 if n else True,
    "most_records_have_authors":        (counts["authors"]/n) >= 0.9 if n else True,
    "all_journals_named":               counts["journal"] == n,
    "all_years_in_range":               counts["year"] == n,
    "all_records_have_pub_types":       counts["pub_types"] == n,
})

print("Script checks:")
for k, v in checks.items():
    print(f"  {'OK  ' if v else 'FAIL'}  {k}")
if issues:
    print(f"\\nPer-record issues ({len(issues)}):")
    for it in issues[:5]:
        print(f"  {it['pmid']}: {'; '.join(it['issues'])}")
    if len(issues) > 5:
        print(f"  …and {len(issues)-5} more")

with open("stage_01/eval/eval_script.json", "w") as f:
    json.dump({"script": checks, "per_record_issues": issues}, f, indent=2)
n_pass = sum(1 for v in checks.values() if v); n_total = len(checks)
score_path = "stage_01/eval/score.json"
score = json.load(open(score_path)) if os.path.exists(score_path) else {}
score["script"] = {"passed": n_pass, "total": n_total,
                   "percent": round(100*n_pass/n_total, 1)}
with open(score_path, "w") as f: json.dump(score, f, indent=2)
print(f"\\nScore: {n_pass}/{n_total} ({score['script']['percent']}%)")""",
    skip_copy="""\
import os, shutil
os.makedirs("stage_01/data", exist_ok=True)
shutil.copy("reference_outputs/stage_01/data/pmids.json",
            "stage_01/data/pmids.json")
print("copied reference Stage 1 output")""",
)


# ---------- Stage 2 ----------
stage_notebook(
    num=2, name="screen",
    inputs_intro="The CRITERIA string is the prompt the LLM sees. Edit it to "
                 "change what gets included. (Also persisted to "
                 "`stage_02/input.txt`/`criteria.txt` so the standalone "
                 "`eval/eval_02_llm.py` keeps working.)",
    inputs_cell="""\
MODEL = "gpt-5.4-nano"
SLEEP_SECONDS = 1.0

CRITERIA = '''\\
Include: primary research papers (2025-2026) reporting at least one
in-vivo mammalian study arm in support of monoclonal antibody (mAb)
development. Eligible study arms include:
  - pharmacokinetics (PK) or toxicokinetics
  - single-dose or repeat-dose toxicology
  - immunogenicity / anti-drug antibody (ADA) assessment
  - tissue biodistribution
  - tissue cross-reactivity confirmed in vivo

Eligible species: mouse, rat, cynomolgus monkey, rhesus monkey, dog,
rabbit, minipig.

Exclude:
  - reviews, meta-analyses, perspectives, commentaries, editorials
  - papers reporting only in-vitro binding, cell-line, or PBMC work
    with no in-vivo arm
  - veterinary mAb studies (animal as patient, not as preclinical model)
  - discovery-stage efficacy-only papers using mouse xenograft tumor
    models with no PK/tox/immunogenicity arm
  - mAb-conjugate papers where the conjugate is the primary subject
  - case reports of mAb adverse events in patients
'''

# Persist for backward compat with the standalone eval_02_llm.py.
import os
os.makedirs("stage_02", exist_ok=True)
with open("stage_02/criteria.txt", "w") as f: f.write(CRITERIA)
with open("stage_02/input.txt", "w") as f:
    f.write(f"MODEL = {MODEL}\\nCRITERIA_FILE = stage_02/criteria.txt\\n"
            f"SLEEP_SECONDS = {SLEEP_SECONDS}\\n")
print(f"MODEL={MODEL}  SLEEP={SLEEP_SECONDS}s  criteria: {len(CRITERIA)} chars")""",
    spec="""\
Write Python that:

1. Reads `stage_01/data/pmids.json` and pulls out the `records` list.
2. For each record, calls OpenAI `chat.completions.create` with the
   MODEL from the inputs cell, the CRITERIA string inlined into the
   prompt, and the record's title + abstract. Use
   `temperature=0` and `response_format={"type": "json_object"}`.
3. Parses each response as JSON with shape
   `{"verdict": "include"|"exclude", "rationale": "<one sentence>"}`.
4. Builds a list `screened` — one dict per record carrying
   `pmid`, `title`, `abstract`, `pub_types`, `verdict`, `rationale`.

Do NOT save to disk — the next cell handles persistence.""",
    gotchas="""\
- **Use the OpenAI JSON-mode response format.** Pass
  `response_format={"type": "json_object"}` AND `temperature=0` so the
  output is parseable without regex.
- **`OpenAI()` reads the env var.** As long as you've bridged the
  Colab secret in Section 1, no explicit api_key arg.
- **Rate-limit yourself.** `time.sleep(SLEEP_SECONDS)` between
  requests (the free tier rate-limits aggressively).
- **Strip everything you don't need from the record before saving.**
  Carrying every metadata field forward bloats the output.
""",
    seed="""\
import json, os, time
from openai import OpenAI
client = OpenAI()  # reads OPENAI_API_KEY from os.environ

# Load Stage 1 records.
with open("stage_01/data/pmids.json") as f:
    records = json.load(f)["records"]

# Produce a variable named `screened` (list of dicts) for the inspect cell.
""",
    inspect_output="""\
import json, os
os.makedirs("stage_02/data", exist_ok=True)
with open("stage_02/data/screened.json", "w") as f:
    json.dump(screened, f, indent=2)
n_inc = sum(1 for r in screened if r['verdict']=='include')
print(f"Saved {len(screened)} rows → stage_02/data/screened.json")
print(f"Verdict: {n_inc} include / {len(screened)-n_inc} exclude\\n")
print("Sample (first 3 include + first 3 exclude):")
inc = [r for r in screened if r['verdict']=='include'][:3]
exc = [r for r in screened if r['verdict']=='exclude'][:3]
for r in inc + exc:
    tag = '✓' if r['verdict']=='include' else '✗'
    print(f"  {tag} PMID {r['pmid']}: {r['rationale'][:100]}")""",
    eval_inline="""\
# Same checks as eval/eval_02_script.py, inlined.
import json, os
os.makedirs("stage_02/eval", exist_ok=True)
with open("stage_02/data/screened.json") as f:
    recs = json.load(f)
checks = {
    "every_record_has_pmid":   all(r.get("pmid") for r in recs),
    "verdicts_valid":          all(r.get("verdict") in {"include","exclude"} for r in recs),
    "rationales_non_empty":    all((r.get("rationale") or "").strip() for r in recs),
}
print("Script checks:")
for k, v in checks.items():
    print(f"  {'OK  ' if v else 'FAIL'}  {k}")
with open("stage_02/eval/eval_script.json", "w") as f:
    json.dump({"script": checks}, f, indent=2)
n_pass = sum(1 for v in checks.values() if v); n_total = len(checks)
score_path = "stage_02/eval/score.json"
score = json.load(open(score_path)) if os.path.exists(score_path) else {}
score["script"] = {"passed": n_pass, "total": n_total,
                   "percent": round(100*n_pass/n_total, 1)}
with open(score_path, "w") as f: json.dump(score, f, indent=2)
print(f"\\nScore: {n_pass}/{n_total} ({score['script']['percent']}%)")
print("\\nOptional AI-grader (costs ~$0.02):")
print("  !python eval/eval_02_llm.py")""",
    skip_copy="""\
import os, shutil
os.makedirs("stage_02/data", exist_ok=True)
shutil.copy("reference_outputs/stage_02/data/screened.json",
            "stage_02/data/screened.json")
print("copied reference Stage 2 output")""",
)


# ---------- Stage 3 ----------
stage_notebook(
    num=3, name="download_fulltext",
    spec="""\
For every PMID in `stage_02/data/screened.json` with verdict='include',
emit ONE artifact under `stage_03/data/`:

  PMC<id>.pdf   ← OA PDF when available
  PMC<id>.xml   ← JATS XML fallback
  <pmid>.json   ← Stage 1 metadata fallback (no fulltext available)

Build a dict `fetched` mapping PMID → path (no nulls — every included
PMID gets at least metadata). The next cell saves it as
`stage_03/data/fetched.json`.

Pipeline:

  1. PMID → PMCID via NCBI ID Converter
     (https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/).
  2. PMCID → OA PDF URL via NCBI's PMC OA service
     (https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi).
  3. If no PDF (or PDF download fails), fall back to JATS XML via
     efetch.fcgi?db=pmc&id=<numeric>.
  4. If both fail, write the stage_01 metadata record as
     `stage_03/data/<pmid>.json`.""",
    gotchas="""\
- **THE BIG ONE.** `oa.fcgi` returns FTP URLs like
  `ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf/<dir>/<file>.pdf`. NCBI
  moved these files to
  `https://ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/oa_pdf/...` in April
  2026 *without updating oa.fcgi's response*. You MUST rewrite the URL
  before downloading. Gemini will not know this.
- **Don't use EuropePMC's getPdf** — currently HTTP 500.
- **Don't use `pmc.ncbi.nlm.nih.gov/articles/.../pdf/`** — gated by a
  JS proof-of-work; scripted clients get an HTML page, not a PDF.
- **Verify downloaded bytes.** A PDF starts with `%PDF`; a JATS XML
  body contains `<article` within the first few KB. Reject responses
  that don't match.
- **Be polite.** `time.sleep(0.4)` between NCBI calls.
""",
    seed="""\
import json, os, time, urllib.request
import xml.etree.ElementTree as ET
HEADERS = {"User-Agent": "ar-bic-2026/0.1"}

with open("stage_02/data/screened.json") as f:
    included = [r for r in json.load(f) if r["verdict"] == "include"]
with open("stage_01/data/pmids.json") as f:
    metadata_by_pmid = {r["pmid"]: r for r in json.load(f)["records"]}

os.makedirs("stage_03/data", exist_ok=True)
# Produce a dict named `fetched` mapping PMID → path for the inspect cell.
""",
    inspect_output="""\
import json, os
with open("stage_03/data/fetched.json", "w") as f:
    json.dump(fetched, f, indent=2)
n_pdf  = sum(1 for v in fetched.values() if v.endswith(".pdf"))
n_xml  = sum(1 for v in fetched.values() if v.endswith(".xml"))
n_meta = sum(1 for v in fetched.values() if v.endswith(".json"))
print(f"Saved fetched.json — {len(fetched)} entries:")
print(f"  {n_pdf} PDF, {n_xml} XML, {n_meta} metadata-only fallback\\n")
for pmid, path in list(fetched.items())[:8]:
    size_kb = os.path.getsize(path) // 1024
    kind = path.split('.')[-1]
    print(f"  {pmid} → {os.path.basename(path):28s} {size_kb:>5d} KB ({kind})")""",
    eval_inline="""\
# Same checks as eval/eval_03_script.py, inlined.
import json, os
os.makedirs("stage_03/eval", exist_ok=True)
with open("stage_02/data/screened.json") as f:
    included = [r for r in json.load(f) if r["verdict"] == "include"]
with open("stage_03/data/fetched.json") as f:
    fetched = json.load(f)

errors = []
for pmid, path in fetched.items():
    if not path:                       errors.append(f"{pmid}: no path"); continue
    if not os.path.exists(path):       errors.append(f"{pmid} -> {path} missing"); continue
    floor = 100 if path.endswith(".json") else 10_000
    if os.path.getsize(path) < floor:
        errors.append(f"{pmid} -> {path} too small ({os.path.getsize(path)}B, floor {floor})")

n_inc  = len(included)
n_pdf  = sum(1 for v in fetched.values() if v and v.endswith(".pdf"))
n_xml  = sum(1 for v in fetched.values() if v and v.endswith(".xml"))
n_meta = sum(1 for v in fetched.values() if v and v.endswith(".json"))
n_full = n_pdf + n_xml

checks = {
    "every_included_pmid_has_entry":
        set(r["pmid"] for r in included) <= set(fetched.keys()),
    "every_pmid_has_artifact":   all(v for v in fetched.values()),
    "no_missing_or_undersized_files": not errors,
    "fulltext_coverage_realistic":
        0 < n_full <= n_inc if n_inc else True,
    "kinds_account_for_all_pmids": (n_inc - n_full - n_meta) == 0,
}
print("Script checks:")
for k, v in checks.items():
    print(f"  {'OK  ' if v else 'FAIL'}  {k}")
if errors:
    print("Errors:")
    for e in errors: print(f"    {e}")
print(f"\\nCoverage: {n_full}/{n_inc} fulltext ({n_pdf} PDF + {n_xml} XML), {n_meta} metadata fallback")

summary = {"included": n_inc, "fulltext": n_full, "pdf": n_pdf,
           "xml": n_xml, "metadata_only": n_meta,
           "fulltext_ratio": round(n_full/n_inc, 3) if n_inc else 0.0,
           "errors": errors}
with open("stage_03/eval/eval_script.json", "w") as f:
    json.dump({"script": checks, "summary": summary}, f, indent=2)
n_pass = sum(1 for v in checks.values() if v); n_total = len(checks)
score_path = "stage_03/eval/score.json"
score = json.load(open(score_path)) if os.path.exists(score_path) else {}
score["script"] = {"passed": n_pass, "total": n_total,
                   "percent": round(100*n_pass/n_total, 1)}
with open(score_path, "w") as f: json.dump(score, f, indent=2)
print(f"\\nScore: {n_pass}/{n_total} ({score['script']['percent']}%)")""",
    skip_copy="""\
import os, shutil, glob
os.makedirs("stage_03/data", exist_ok=True)
for src in glob.glob("reference_outputs/stage_03/data/*"):
    shutil.copy(src, "stage_03/data/")
print("copied reference Stage 3 output:")
print(sorted(os.listdir("stage_03/data")))""",
    fallback_post=("**Note:** The reference Stage 3 output ships only the XML + "
                   "metadata-only JSON fallbacks (no PDFs — too large to commit). "
                   "Stage 4 handles all three input shapes, so the workshop still "
                   "works end-to-end without the PDFs."),
)


# ---------- Stage 4 ----------
stage_notebook(
    num=4, name="pdf_to_text",
    spec="""\
Convert every artifact under `stage_03/data/` to a `.md` under
`stage_04/data/`. Handle three input shapes uniformly:

  *.pdf  → run `lit parse <path> -o <tmp>.txt` and read the result
  *.xml  → walk JATS: emit `# <title>`, `## Abstract`, paragraphs, and
           heading-rendered <sec> structure. Drop figures, refs, math.
  *.json → render Stage 3 metadata fallback as title + abstract +
           authors/journal footer.

Both XML and metadata-fallback outputs should emit an authors/journal/
year/pub_types footer so the Stage 5 extractor sees a consistent shape.""",
    gotchas="""\
- **liteparse is a Node CLI, not a Python lib.** Invoke via
  `subprocess.run(["lit", "parse", path, "-o", tmp_path], check=True)`.
  Installed in Section 1.
- **JATS uses `<sec>` and `<p>`.** Recurse with `element.iter()` or a
  depth-tracking walker — don't grab only top-level paragraphs.
- **Authors live in `<front>//<contrib-group>//<contrib>`** in JATS,
  with `<surname>` + `<given-names>` children. Bodies have no author
  byline — without a footer, Stage 5 hallucinates first_author.
- **`itertext()` again.** Same trick as Stage 1 for any element that
  might wrap inline children.
- **Floor each output.** Fulltext output should be much larger than an
  abstract — assert `getsize > 5_000` (or `> 500` for the JSON
  fallback) to catch parse failures early.
""",
    seed="""\
import glob, json, os, re, subprocess, tempfile
import xml.etree.ElementTree as ET
os.makedirs("stage_04/data", exist_ok=True)
# Read inputs from stage_03/data/*.{pdf,xml,json} and write
# stage_04/data/<stem>.md for each. The inspect cell will glob the
# results — no Python output variable required.
""",
    inspect_output="""\
import glob, os
mds = sorted(glob.glob("stage_04/data/*.md"))
print(f"{len(mds)} .md files in stage_04/data/\\n")
for p in mds:
    kb = os.path.getsize(p) // 1024
    stem = os.path.splitext(os.path.basename(p))[0]
    with open(p) as f:
        first = f.readline().strip()[:78]
    print(f"  {stem:18s} {kb:>5d} KB   {first}")""",
    eval_inline="""\
# Same checks as eval/eval_04_script.py, inlined.
import json, os, re
os.makedirs("stage_04/eval", exist_ok=True)
with open("stage_03/data/fetched.json") as f:
    fetched = json.load(f)
with open("stage_02/data/screened.json") as f:
    abstract_by_pmid = {r["pmid"]: r["abstract"] for r in json.load(f)}

def first_words(s, n=80):
    return re.sub(r"\\s+", " ", (s or "")).strip()[:n]
def alnum(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())
def _floor(path):
    return 500 if path.endswith(".json") else 5_000

errors, items = [], []
for pmid, path in fetched.items():
    if not path: continue
    stem = os.path.splitext(os.path.basename(path))[0]
    text_path = f"stage_04/data/{stem}.md"
    if not os.path.exists(text_path):
        errors.append(f"{pmid} ({stem}): text missing")
        items.append({"pmid": pmid, "stem": stem, "size_ok": False, "abstract_roundtrip": False})
        continue
    size_ok = os.path.getsize(text_path) > _floor(path)
    text = open(text_path).read()
    needle = first_words(abstract_by_pmid.get(pmid, ""))
    rt = bool(needle) and alnum(needle) in alnum(text)
    items.append({"pmid": pmid, "stem": stem, "size_ok": size_ok,
                  "abstract_roundtrip": rt, "needle": needle})
    if not size_ok: errors.append(f"{pmid} ({stem}): < size floor")
    if not rt and needle: errors.append(f"{pmid} ({stem}): abstract doesn't round-trip")

n_files = len(items)
n_size_ok = sum(1 for it in items if it["size_ok"])
n_rt = sum(1 for it in items if it["abstract_roundtrip"])
checks = {
    "every_screened_paper_has_text": all(
        os.path.exists(f"stage_04/data/{os.path.splitext(os.path.basename(p))[0]}.md")
        for p in fetched.values() if p),
    "all_files_above_size_floor":  n_size_ok == n_files,
    "all_abstracts_round_trip":    n_rt == n_files,
}
print("Script checks:")
for k, v in checks.items():
    print(f"  {'OK  ' if v else 'FAIL'}  {k}")
if errors:
    print("Errors:")
    for e in errors: print(f"    {e}")
print(f"\\nRound-trip: {n_rt}/{n_files} abstract prefixes match converted text")

with open("stage_04/eval/eval_script.json", "w") as f:
    json.dump({"script": checks, "items": items}, f, indent=2)
n_pass = sum(1 for v in checks.values() if v); n_total = len(checks)
score_path = "stage_04/eval/score.json"
score = json.load(open(score_path)) if os.path.exists(score_path) else {}
score["script"] = {"passed": n_pass, "total": n_total,
                   "percent": round(100*n_pass/n_total, 1)}
with open(score_path, "w") as f: json.dump(score, f, indent=2)
print(f"\\nScore: {n_pass}/{n_total} ({score['script']['percent']}%)")""",
    skip_copy="""\
import os, shutil, glob
os.makedirs("stage_04/data", exist_ok=True)
for src in glob.glob("reference_outputs/stage_04/data/*.md"):
    shutil.copy(src, "stage_04/data/")
print(f"copied {len(os.listdir('stage_04/data'))} reference .md files")""",
)


# ---------- Stage 5 ----------
stage_notebook(
    num=5, name="extract",
    inputs_intro="The SCHEMA string is the extraction contract — what fields "
                 "the LLM must produce, with type/enum hints. Edit MODEL or "
                 "SCHEMA below; the cell also writes `schema.json` to the "
                 "repo root for the standalone eval scripts.",
    inputs_cell="""\
MODEL = "gpt-5.4-nano"

SCHEMA = '''\\
{
  "pmid": "string",
  "source_type": "fulltext | abstract-only",
  "first_author": "string",
  "year": "integer",
  "mab_name": "string | null",
  "target": "string",
  "format": "IgG1 | IgG2 | IgG3 | IgG4 | bispecific | ADC | Fab | Fc-fusion | other",
  "development_stage": "discovery | lead optimization | IND-enabling | clinical translation | post-approval",
  "regulatory_context": "none-stated | IND-supporting | BLA-supporting | post-marketing",
  "threeRs_mentioned": "boolean",
  "author_reduction_recommendation": "string | null",
  "animal_arms": [
    {
      "species": "mouse | rat | cynomolgus | rhesus | dog | rabbit | minipig | other",
      "n_animals": "integer | null",
      "study_type": "PK | single-dose tox | repeat-dose tox | immunogenicity | biodistribution | efficacy | TCR",
      "duration_days": "integer | null",
      "species_justification": "pharmacological relevance | regulatory expectation | historical precedent | not stated",
      "cross_reactivity_evidence": "in-vitro binding shown | sequence homology only | not addressed",
      "endpoints_unique_to_animal": "string | null",
      "concurrent_nam": "string | null"
    }
  ],
  "nams_discussed": [
    {"method": "string", "context": "future work | limitation discussion | literature comparison"}
  ]
}
'''
with open("schema.json", "w") as f: f.write(SCHEMA)
print(f"MODEL={MODEL}  SCHEMA: {len(SCHEMA)} chars (also written to schema.json)")""",
    spec="""\
For every `stage_04/data/*.md`, call OpenAI with MODEL and a prompt
that includes the SCHEMA string. Get back a JSON object per paper
matching the schema's shape.

The schema is a TYPE CONTRACT, not literal values — each field's
value is the TYPE of the data to extract, not the type label itself.

After the LLM returns each record:
  1. Force-overwrite `pmid` and `source_type` from the
     `stage_03/data/fetched.json` mapping (build a stem→pmid map and
     a stem→source_type map first). Never trust the LLM for IDs.
  2. Run a cheap hallucination check on `concurrent_nam`: any value
     whose substantive tokens (>4 chars) don't appear in the source
     text gets demoted to `nams_discussed` (keeps it visible but
     out of the structured arm).

Save each record to `stage_05/data/<stem>.json` (one file per paper).""",
    gotchas="""\
- **No regex fallback for this stage.** It hard-fails without
  `OPENAI_API_KEY`. Bail with an assert.
- **JSON mode required.** `response_format={"type": "json_object"}`
  and `temperature=0`.
- **PMC stem → PMID** comes from `stage_03/data/fetched.json` — build
  the map up front and inject the pmid into the prompt so the LLM
  doesn't invent one.
- **Source type matters.** Tag each record `fulltext` (path ends
  `.pdf`/`.xml`) vs `abstract-only` (path ends `.json`). For
  abstract-only the LLM should return `[]` for `animal_arms` rather
  than guessing from a brief PubMed abstract.
""",
    seed="""\
import glob, json, os, time
assert os.environ.get("OPENAI_API_KEY"), \\
    "extraction needs OPENAI_API_KEY (no fallback)"
from openai import OpenAI
client = OpenAI()
os.makedirs("stage_05/data", exist_ok=True)

with open("stage_03/data/fetched.json") as f:
    PMID_BY_PATH = json.load(f)
STEM_TO_PMID = {}
STEM_TO_SOURCE = {}
for pmid, path in PMID_BY_PATH.items():
    if not path: continue
    stem = os.path.splitext(os.path.basename(path))[0]
    STEM_TO_PMID[stem] = pmid
    STEM_TO_SOURCE[stem] = "fulltext" if path.endswith((".pdf", ".xml")) else "abstract-only"
""",
    inspect_output="""\
import glob, json, os
SKIP = {"eval_script.json", "eval_llm.json", "score.json"}
extractions = []
for p in sorted(glob.glob("stage_05/data/*.json")):
    if os.path.basename(p) in SKIP: continue
    extractions.append((p, json.load(open(p))))
print(f"{len(extractions)} extractions in stage_05/data/\\n")
total_arms = 0
for path, rec in extractions:
    arms = rec.get("animal_arms") or []
    total_arms += len(arms)
    stem = os.path.splitext(os.path.basename(path))[0]
    print(f"  {stem:18s}  pmid={rec.get('pmid','?'):10s}  "
          f"src={rec.get('source_type','?'):14s}  arms={len(arms)}")
    for a in arms[:2]:
        print(f"      • {a.get('species','?')} / {a.get('study_type','?')} "
              f"n={a.get('n_animals')} {a.get('duration_days','?')}d")
print(f"\\nTotal animal_arms across papers: {total_arms}")""",
    eval_inline="""\
# Same checks as eval/eval_05_script.py, inlined.
import glob, json, os
os.makedirs("stage_05/eval", exist_ok=True)
ENUM_SOURCE = {"fulltext", "abstract-only"}
ENUM_FORMAT = {"IgG1","IgG2","IgG3","IgG4","bispecific","ADC","Fab","Fc-fusion","other"}
ENUM_STAGE  = {"discovery","lead optimization","IND-enabling","clinical translation","post-approval"}
ENUM_REG    = {"none-stated","IND-supporting","BLA-supporting","post-marketing"}
ENUM_SPECIES= {"mouse","rat","cynomolgus","rhesus","dog","rabbit","minipig","other"}
ENUM_STUDY  = {"PK","single-dose tox","repeat-dose tox","immunogenicity","biodistribution","efficacy","TCR"}
ENUM_JUSTIF = {"pharmacological relevance","regulatory expectation","historical precedent","not stated"}
ENUM_CR     = {"in-vitro binding shown","sequence homology only","not addressed"}
SKIP = {"eval.json","eval_script.json","eval_llm.json","score.json"}

rows = []
for jp in sorted(glob.glob("stage_05/data/*.json")):
    if os.path.basename(jp) in SKIP: continue
    rec = json.load(open(jp))
    arms = rec.get("animal_arms") or []
    enums_ok = (
        rec.get("format") in ENUM_FORMAT | {None}
        and rec.get("development_stage") in ENUM_STAGE | {None}
        and rec.get("regulatory_context") in ENUM_REG | {None}
        and all(a.get("species") in ENUM_SPECIES | {None}
                and a.get("study_type") in ENUM_STUDY | {None}
                and a.get("species_justification") in ENUM_JUSTIF | {None}
                and a.get("cross_reactivity_evidence") in ENUM_CR | {None}
                for a in arms)
    )
    numerics_ok = all(
        (a.get("n_animals") is None or (isinstance(a.get("n_animals"), int) and a["n_animals"] >= 0))
        and (a.get("duration_days") is None or (isinstance(a.get("duration_days"), int) and a["duration_days"] >= 0))
        for a in arms
    )
    rows.append({
        "stem": os.path.splitext(os.path.basename(jp))[0],
        "pmid": rec.get("pmid"),
        "has_required_keys": bool(rec.get("pmid")) and isinstance(arms, list),
        "source_type_valid": rec.get("source_type") in ENUM_SOURCE,
        "enums_within_vocab": enums_ok,
        "numerics_non_negative": numerics_ok,
    })

print("Script checks (per paper):")
for r in rows:
    flags = " ".join("OK  " if r[k] else "FAIL"
        for k in ("has_required_keys","source_type_valid","enums_within_vocab","numerics_non_negative"))
    print(f"  {r['stem']:18s} keys/src/enums/numerics  {flags}")

with open("stage_05/eval/eval_script.json", "w") as f:
    json.dump({"script_per_paper": rows}, f, indent=2)
KEYS = ("has_required_keys","source_type_valid","enums_within_vocab","numerics_non_negative")
n_pass = sum(1 for r in rows for k in KEYS if r[k])
n_total = len(rows) * len(KEYS)
score_path = "stage_05/eval/score.json"
score = json.load(open(score_path)) if os.path.exists(score_path) else {}
score["script"] = {"passed": n_pass, "total": n_total,
                   "percent": round(100*n_pass/n_total, 1) if n_total else 0.0}
with open(score_path, "w") as f: json.dump(score, f, indent=2)
print(f"\\nScore: {n_pass}/{n_total} ({score['script']['percent']}%)")
print("\\nOptional AI-grader (costs ~$0.10):")
print("  !python eval/eval_05_llm.py")""",
    skip_copy="""\
import os, shutil, glob
os.makedirs("stage_05/data", exist_ok=True)
for src in glob.glob("reference_outputs/stage_05/data/*.json"):
    shutil.copy(src, "stage_05/data/")
print(f"copied {len(os.listdir('stage_05/data'))} reference extractions")""",
)


# ---------- Stage 6 ----------
stage_notebook(
    num=6, name="table",
    spec="""\
Flatten every `stage_05/data/*.json` into one row per
(paper × animal_arm) and write
`stage_06/data/mabs_animal_studies.csv` with these columns (in order):

  pmid, source_type, first_author, year, mab_name, target, format,
  development_stage, regulatory_context, threeRs_mentioned,
  author_reduction_recommendation, species, n_animals, study_type,
  duration_days, species_justification, cross_reactivity_evidence,
  endpoints_unique_to_animal, concurrent_nam, n_nams_discussed

`n_nams_discussed` is `len(rec["nams_discussed"])` — a count, not a list.

A paper with no animal_arms contributes zero rows. The header is always
written.

Skip any sibling JSON named `eval.json`, `eval_script.json`,
`eval_llm.json`, or `score.json`.""",
    gotchas="""\
- **Use `csv.DictWriter(f, fieldnames=FIELDNAMES)`.** Keeps column
  order deterministic even when some arms are missing fields.
- **Open with `newline=""`** to avoid blank lines on Windows runtimes.
- **A paper-level `nams_discussed` list** needs `len(...)` not the
  list itself written to the cell.
- **Skip eval artifacts in the directory** (see spec).
""",
    seed="""\
import csv, glob, json, os
os.makedirs("stage_06/data", exist_ok=True)
SKIP_NAMES = {"eval.json", "eval_script.json", "eval_llm.json", "score.json"}
# Build a list `rows` of dicts (one per animal_arm), then write the CSV.
""",
    inspect_output="""\
import csv
with open("stage_06/data/mabs_animal_studies.csv") as f:
    csv_rows = list(csv.DictReader(f))
print(f"{len(csv_rows)} animal-arm rows in stage_06/data/mabs_animal_studies.csv\\n")
print("Sample (first 5 rows):")
for r in csv_rows[:5]:
    print(f"  PMID {r['pmid']:>10s} | {r['species']:>10s} | "
          f"{r['study_type']:>18s} | n={r.get('n_animals','?'):>4s} | "
          f"target={(r.get('target') or '')[:24]}")
n_nam = sum(1 for r in csv_rows if (r.get('concurrent_nam') or '').strip())
print(f"\\n{n_nam}/{len(csv_rows)} rows have a concurrent_nam.")""",
    eval_inline="""\
# Same checks as eval/eval_06_script.py, inlined.
import csv, glob, json, os
from collections import Counter

os.makedirs("stage_06/eval", exist_ok=True)
REQUIRED_COLUMNS = {
    "pmid","species","study_type","year","mab_name","target","format",
    "development_stage","regulatory_context","threeRs_mentioned","n_animals",
    "duration_days","species_justification","cross_reactivity_evidence",
    "endpoints_unique_to_animal","concurrent_nam","n_nams_discussed",
    "author_reduction_recommendation","first_author",
}
SKIP = {"eval.json","eval_script.json","eval_llm.json","score.json"}

with open("stage_06/data/mabs_animal_studies.csv") as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    columns = set(reader.fieldnames or [])

errors = []
for r in rows:
    if not r.get("pmid"):       errors.append("row missing pmid")
    if not r.get("species"):    errors.append(f"row {r.get('pmid')}: missing species")
    if not r.get("study_type"): errors.append(f"row {r.get('pmid')}: missing study_type")
    if r.get("n_animals"):
        try:
            if int(r["n_animals"]) < 0:
                errors.append(f"row {r.get('pmid')}: negative n_animals")
        except ValueError:
            errors.append(f"row {r.get('pmid')}: non-integer n_animals")

def _extracted_records():
    for p in glob.glob("stage_05/data/*.json"):
        if os.path.basename(p) in SKIP: continue
        yield json.load(open(p))

checks = {
    "row_count_matches_arms":
        len(rows) == sum(len(r.get("animal_arms") or []) for r in _extracted_records()),
    "required_columns_present": REQUIRED_COLUMNS <= columns,
    "no_row_errors":            not errors,
}
print("Script checks:")
for k, v in checks.items():
    print(f"  {'OK  ' if v else 'FAIL'}  {k}")
if errors:
    print("Errors:")
    for e in errors: print(f"    {e}")

crosstab = Counter((r["species"], r["study_type"]) for r in rows)
n_with_nam = sum(1 for r in rows if (r.get("concurrent_nam") or "").strip())
print(f"\\nRows: {len(rows)}  |  with concurrent_nam: {n_with_nam}")
print("species × study_type:")
for (sp, st), n in sorted(crosstab.items()):
    print(f"  {sp:12s} × {st:18s}  {n}")

with open("stage_06/eval/eval_script.json", "w") as f:
    json.dump({
        "script": checks,
        "n_rows": len(rows),
        "n_with_concurrent_nam": n_with_nam,
        "crosstab": [{"species": sp, "study_type": st, "n": n}
                     for (sp, st), n in crosstab.items()],
        "errors": errors,
    }, f, indent=2)

n_pass = sum(1 for v in checks.values() if v); n_total = len(checks)
score_path = "stage_06/eval/score.json"
score = json.load(open(score_path)) if os.path.exists(score_path) else {}
score["script"] = {"passed": n_pass, "total": n_total,
                   "percent": round(100*n_pass/n_total, 1)}
with open(score_path, "w") as f: json.dump(score, f, indent=2)
print(f"\\nScore: {n_pass}/{n_total} ({score['script']['percent']}%)")""",
    skip_copy="""\
import os, shutil
os.makedirs("stage_06/data", exist_ok=True)
shutil.copy("reference_outputs/stage_06/data/mabs_animal_studies.csv",
            "stage_06/data/mabs_animal_studies.csv")
print("copied reference Stage 6 output")""",
)
