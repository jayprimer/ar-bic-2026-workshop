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

def stage_notebook(num, name, spec, gotchas, seed, verify, eval_cmd,
                   skip_copy, fallback_post=""):
    cells = [
        md(f"# Stage {num} — {name}\n\n"
           "Re-create this stage's script with Gemini's help. The cells "
           "below give you the spec, the seed, the gotchas, and a "
           "verification step. The implementation itself is yours to write."),

        md("## 1. Setup\n\n"
           "Every cell in this section is idempotent and safe to re-run. "
           "If you opened this notebook fresh (without running Stage 0 "
           "first in the same runtime), run all of them now."),

        md("### 1a. Clone the repo and `cd` into it"),
        BOOTSTRAP,

        md("### 1b. Install dependencies\n\n"
           "Python (`openai`) and the Node CLI `@llamaindex/liteparse`. "
           "First run takes ~30s; re-runs are near-instant."),
        DEPS,

        md(("### 1c. Bridge your OpenAI key\n\n"
            "Add `OPENAI_API_KEY` in Colab's Secrets panel (key icon, left "
            "sidebar) and toggle notebook access first.")
           if num in (2, 5) else
           "### 1c. (no API key needed for this stage)"),
        KEY_BRIDGE if num in (2, 5) else code("# This stage doesn't call the OpenAI API."),

        md("### 1d. Stage the bundle-shipped configs"),
        STAGE_CONFIGS,
    ]
    prior = load_prior_outputs_cell(num)
    if prior:
        cells += [
            md(f"### 1e. Load prior stages' reference outputs\n\n"
               f"Stage {num} reads outputs from earlier stages. Each Colab "
               "notebook gets its own runtime, so work done in another "
               "notebook is not visible here. This cell seeds "
               f"`stage_01..stage_{num-1:02d}/data/` from the canonical "
               f"reference run so Stage {num} has inputs to work with."),
            prior,
        ]

    cells += [
        md(f"## 2. Spec — paste this into Gemini\n\n"
           "Open the Gemini side panel in Colab (sparkles icon, top right) "
           "and paste the block below as your prompt. Then iterate.\n\n"
           f"```\n{spec}\n```"),

        md("## 3. Gotchas Gemini probably won't know\n\n"
           "Copy any that apply into Gemini if it goes off-track:\n\n" + gotchas),

        md("## 4. Seed — a few lines to anchor Gemini in the right direction"),
        code(seed),

        md("## 5. Your implementation\n\n"
           "Drive Gemini to fill this in. Iterate until the verification cell "
           "below passes."),
        code(f"# TODO: implement Stage {num} here.\n"
             "# Read the spec above. Use the seed cell's imports.\n"
             "# When done, run the verification cell next.\n"),

        md("## 6. Verify"),
        code(verify),

        md(f"## 7. Run the eval grader\n\n"
           "The eval reads only your stage's output and writes "
           f"`stage_{num:02d}/eval/eval_*.json` + `score.json`."),
        code(eval_cmd),
    ]
    if fallback_post:
        cells.append(md(fallback_post))

    cells += [
        md(f"## 8. Stuck? Skip this stage\n\n"
           f"Copy the reference run's Stage {num} output into place so the "
           "next stage's notebook can still run. Use this sparingly — "
           "the point of the workshop is to *re-create* each stage."),
        code(skip_copy),
    ]
    write(f"stage_{num:02d}_{name.lower().replace(' ', '_')}.ipynb", cells)


# ---------- Stage 1 ----------
stage_notebook(
    num=1, name="search",
    spec="""\
Write a Python script (a single file run top-to-bottom) that:

1. Reads PubMed search config from `stage_01/input.txt`. The format is
   `KEY = value` per line, '#' comments, indented continuation lines
   joined with one space. Keys: QUERY (required), N (default 30), TOOL,
   EMAIL.
2. Calls NCBI E-utilities `esearch.fcgi` (db=pubmed, retmax=N,
   retmode=json, sort=date) to get N PMIDs for the query.
3. Calls NCBI E-utilities `efetch.fcgi` (db=pubmed, retmode=xml) for
   those PMIDs to get per-record metadata: pmid, title, abstract,
   authors (list + first_author), journal, year, pub_types.
4. Writes `stage_01/data/pmids.json` with shape:
   `{"query": ..., "n_requested": N, "pmids": [...], "records": [...]}`.
5. Asserts: every record has a non-empty pmid AND a non-empty title.

Use only the standard library (urllib, json, xml.etree.ElementTree).
Do not use Biopython or `requests`.""",
    gotchas="""\
- **Abstracts are nested XML.** Use `el.itertext()` joined together,
  NOT `el.text`, when reading `<ArticleTitle>` and `<AbstractText>`.
  `.text` silently truncates at the first inline child (`<i>`,
  `<sub>`, `<sup>`).
- **Abstract can be multi-part labeled.** Find all
  `.//Abstract/AbstractText`, read each `Label` attribute, and join
  them as `"BACKGROUND: ... METHODS: ..."`.
- **efetch can reorder.** Re-sort `records` to match the esearch
  `pmids` order before writing.
- **Identify yourself to NCBI.** Pass `tool` and `email` URL params
  (anonymous clients are throttled hard).
""",
    seed="""\
import json, os, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

STAGE = "stage_01"
DATA = f"{STAGE}/data"
os.makedirs(DATA, exist_ok=True)
INPUT_PATH = f"{STAGE}/input.txt"
HEADERS = {"User-Agent": "ar-bic-2026/0.1"}
""",
    verify="""\
import json, os
assert os.path.exists("stage_01/data/pmids.json"), "no output file"
d = json.load(open("stage_01/data/pmids.json"))
assert "pmids" in d and "records" in d, "missing keys"
assert len(d["pmids"]) == len(d["records"]), "pmid/record count mismatch"
for r in d["records"]:
    assert r.get("pmid"), "record missing pmid"
    assert r.get("title"), f"{r.get('pmid')}: missing title"
print(f"OK — {len(d['records'])} records")""",
    eval_cmd="!python eval/eval_01_script.py",
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
    spec="""\
Write a Python script that:

1. Reads `stage_02/input.txt` (same KEY=value parser as Stage 1).
   Keys: MODEL (default gpt-5.4-nano), CRITERIA_FILE
   (default stage_02/criteria.txt), SLEEP_SECONDS (default 1.0).
2. Reads `stage_02/criteria.txt` as a plain-text inclusion/exclusion
   prompt.
3. Reads `stage_01/data/pmids.json` → `records` list.
4. For each record, calls OpenAI chat.completions with the criteria
   inlined into the prompt; asks for STRICT JSON
   `{"verdict": "include"|"exclude", "rationale": "<one sentence>"}`.
5. Writes `stage_02/data/screened.json` — a list, one object per
   record, carrying `pmid`, `title`, `abstract`, `pub_types`,
   `verdict`, `rationale`.

Use `temperature=0` and `response_format={"type": "json_object"}`.""",
    gotchas="""\
- **Use the OpenAI JSON-mode response format.** Pass
  `response_format={"type": "json_object"}` AND `temperature=0` so the
  output is parseable without regex.
- **`OpenAI()` reads the env var.** As long as you've bridged the
  Colab secret in the setup cell above, no explicit api_key arg.
- **Rate-limit yourself.** Sleep `SLEEP_SECONDS` between requests
  (the free tier rate-limits aggressively).
- **Strip everything you don't need from the record before writing.**
  Carrying every metadata field forward bloats `screened.json`.
""",
    seed="""\
import json, os, time
STAGE = "stage_02"
DATA = f"{STAGE}/data"
os.makedirs(DATA, exist_ok=True)
INPUT_PATH = f"{STAGE}/input.txt"

# config-file parser from Stage 1 (reuse — or ask Gemini to re-emit it)
""",
    verify="""\
import json, os
assert os.path.exists("stage_02/data/screened.json"), "no output file"
rows = json.load(open("stage_02/data/screened.json"))
for r in rows:
    assert r["pmid"], "missing pmid"
    assert r["verdict"] in {"include", "exclude"}, r
    assert r["rationale"].strip(), "empty rationale"
print(f"OK — {sum(1 for r in rows if r['verdict']=='include')}/{len(rows)} included")""",
    eval_cmd="!python eval/eval_02_script.py\n# Optional (needs API key):\n# !python eval/eval_02_llm.py",
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

Also write `stage_03/data/fetched.json` mapping PMID → path
(no nulls — every included PMID gets at least metadata).

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

STAGE = "stage_03"
DATA = f"{STAGE}/data"
os.makedirs(DATA, exist_ok=True)
HEADERS = {"User-Agent": "ar-bic-2026/0.1"}

with open("stage_02/data/screened.json") as f:
    included = [r for r in json.load(f) if r["verdict"] == "include"]
with open("stage_01/data/pmids.json") as f:
    metadata_by_pmid = {r["pmid"]: r for r in json.load(f)["records"]}
""",
    verify="""\
import json, os
fetched = json.load(open("stage_03/data/fetched.json"))
for pmid, path in fetched.items():
    assert os.path.exists(path), f"{pmid}: missing {path}"
    floor = 100 if path.endswith(".json") else 10_000
    assert os.path.getsize(path) > floor, f"{pmid}: too small ({path})"
n_pdf = sum(1 for v in fetched.values() if v.endswith(".pdf"))
n_xml = sum(1 for v in fetched.values() if v.endswith(".xml"))
n_meta = sum(1 for v in fetched.values() if v.endswith(".json"))
print(f"OK — {n_pdf} PDF + {n_xml} XML + {n_meta} metadata fallback")""",
    eval_cmd="!python eval/eval_03_script.py",
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
  Was installed in Stage 0.
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

STAGE = "stage_04"
DATA = f"{STAGE}/data"
IN_DATA = "stage_03/data"
os.makedirs(DATA, exist_ok=True)
""",
    verify="""\
import glob, os
mds = sorted(glob.glob("stage_04/data/*.md"))
assert mds, "no .md files produced"
for p in mds:
    assert os.path.getsize(p) > 500, f"{p}: suspiciously small"
print(f"OK — {len(mds)} .md files")""",
    eval_cmd="!python eval/eval_04_script.py",
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
    spec="""\
For every `stage_04/data/*.md`, call OpenAI gpt-5.4-nano to extract a
JSON record matching `schema.json` (located at repo root). Write to
`stage_05/data/<stem>.json` (one file per paper).

The schema is a TYPE CONTRACT, not literal values. Each field's value
is the TYPE of the data to extract, not the type label itself.

After the LLM returns:
  1. Force-overwrite `pmid` and `source_type` from the
     `stage_03/data/fetched.json` mapping — never trust the LLM for IDs.
  2. Run a cheap hallucination check on `concurrent_nam`: any value
     whose substantive tokens (>4 chars) don't appear in the source
     text gets demoted to `nams_discussed` (keeps it visible for
     review but out of the structured arm).""",
    gotchas="""\
- **No regex fallback for this stage.** It hard-fails without
  `OPENAI_API_KEY`. (`assert os.environ.get("OPENAI_API_KEY")`)
- **JSON mode required.** `response_format={"type": "json_object"}`
  and `temperature=0`.
- **schema.json lives at the REPO ROOT**, not under `configs/`, after
  Stage 0's setup cell copies it.
- **PMC stem → PMID is one-to-many-ish.** Build the stem→pmid map
  from `stage_03/data/fetched.json` and inject the pmid into the
  prompt so the LLM doesn't invent one.
- **Source type matters.** Tag each record `fulltext` vs
  `abstract-only` based on the Stage 3 path extension. The LLM should
  return `[]` for `animal_arms` rather than guessing from a brief
  PubMed abstract.
""",
    seed="""\
import glob, json, os, time
assert os.environ.get("OPENAI_API_KEY"), \\
    "extraction needs OPENAI_API_KEY (no regex fallback)"
from openai import OpenAI

STAGE = "stage_05"
DATA = f"{STAGE}/data"
IN_DATA = "stage_04/data"
os.makedirs(DATA, exist_ok=True)

with open("schema.json") as f:
    SCHEMA = f.read()
""",
    verify="""\
import glob, json, os
outs = sorted(glob.glob("stage_05/data/*.json"))
assert outs, "no extractions produced"
for p in outs:
    if os.path.basename(p) in ("eval_script.json", "eval_llm.json", "score.json"):
        continue
    rec = json.load(open(p))
    assert rec.get("pmid"), f"{p}: no pmid"
    assert isinstance(rec.get("animal_arms"), list), f"{p}: animal_arms not list"
print(f"OK — {len(outs)} extractions")""",
    eval_cmd="!python eval/eval_05_script.py\n# Optional (needs API key, ~$0.10):\n# !python eval/eval_05_llm.py",
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
STAGE = "stage_06"
DATA = f"{STAGE}/data"
IN_DATA = "stage_05/data"
os.makedirs(DATA, exist_ok=True)
SKIP_NAMES = {"eval.json", "eval_script.json", "eval_llm.json", "score.json"}
""",
    verify="""\
import csv, os
out = "stage_06/data/mabs_animal_studies.csv"
assert os.path.exists(out), "no CSV produced"
with open(out) as f:
    rows = list(csv.DictReader(f))
for r in rows:
    assert r["pmid"], "row missing pmid"
    assert r["species"], "row missing species"
    assert r["study_type"], "row missing study_type"
print(f"OK — {len(rows)} animal-arm rows")""",
    eval_cmd="!python eval/eval_06_script.py",
    skip_copy="""\
import os, shutil
os.makedirs("stage_06/data", exist_ok=True)
shutil.copy("reference_outputs/stage_06/data/mabs_animal_studies.csv",
            "stage_06/data/mabs_animal_studies.csv")
print("copied reference Stage 6 output")""",
)
