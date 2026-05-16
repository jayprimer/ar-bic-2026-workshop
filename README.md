# ar-bic-2026 — mAbs animal-study pipeline workshop

Re-create a 6-stage literature-mining pipeline in Google Colab with
help from Colab's Gemini assistant. The pipeline turns a PubMed query
into a structured table of monoclonal-antibody animal-study findings.

Each stage ships as a Colab notebook with a **spec**, a **seed**, and a
**list of gotchas Gemini won't know**. The implementation itself is
yours to write. An eval grader at the end of each stage tells you
whether your output matches the contract.

## Open in Colab

| Stage | Notebook |
|---|---|
| 0 — setup (optional tour) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jayprimer/ar-bic-2026-workshop/blob/main/notebooks/stage_00_setup.ipynb) |
| 1 — search | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jayprimer/ar-bic-2026-workshop/blob/main/notebooks/stage_01_search.ipynb) |
| 2 — screen | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jayprimer/ar-bic-2026-workshop/blob/main/notebooks/stage_02_screen.ipynb) |
| 3 — download fulltext | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jayprimer/ar-bic-2026-workshop/blob/main/notebooks/stage_03_download_fulltext.ipynb) |
| 4 — pdf to text | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jayprimer/ar-bic-2026-workshop/blob/main/notebooks/stage_04_pdf_to_text.ipynb) |
| 5 — extract | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jayprimer/ar-bic-2026-workshop/blob/main/notebooks/stage_05_extract.ipynb) |
| 6 — table | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jayprimer/ar-bic-2026-workshop/blob/main/notebooks/stage_06_table.ipynb) |

**You can jump straight to any stage** — each notebook is fully
self-bootstrapping. Section 1 of every stage notebook clones the repo,
installs dependencies, bridges your OpenAI key, stages the configs, and
seeds the previous stages' outputs from the canonical reference run.

Stage 0 is optional — useful as a guided tour of what setup does, but
not a prerequisite.

## What you'll need

- A Google account (for Colab).
- An OpenAI API key for Stages 2, 5, and the LLM-grader evals. The
  full end-to-end run costs **well under $0.20**. (Stages 1, 3, 4, 6
  and the script-only evals need no key.)
- Patience for the occasional NCBI flake — retry the cell.

## Layout

```
notebooks/           ← one .ipynb per stage; the workshop deliverable
prompts/             ← guidance for driving Gemini effectively
configs/             ← bundle-shipped editable config (query, criteria, schema)
eval/                ← per-stage graders; runs on YOUR output
reference_outputs/   ← archived canonical run, for "skip this stage" fallback
requirements.txt     ← openai (Stage 4 also needs the liteparse Node CLI)
```

## How a stage notebook is structured

Every stage notebook (1–6) has the same eight sections:

1. **Setup (1a–1e)** — clone + cd, install deps, bridge OpenAI key,
   stage configs, and seed previous stages' outputs from the
   canonical reference run. Every cell is idempotent.
2. **Spec card** — the exact contract for this stage. Paste it as
   your first prompt to Gemini.
3. **Gotchas** — things Gemini will not know. Copy them inline when
   needed.
4. **Seed** — a few lines of imports + path setup to anchor Gemini.
5. **Your implementation** — drive Gemini to fill this in.
6. **Verify** — assertions on the output file.
7. **Eval** — the per-stage grader writes a score under
   `stage_NN/eval/`.
8. **Skip this stage** — emergency copy from `reference_outputs/`
   so the next stage's notebook can still run.

See `prompts/gemini_intro.md` for tips on driving the Gemini side panel.

## Costs

Order-of-magnitude estimates for the canonical N=30 query:

- Stage 2 (gpt-5.4-nano, ~30 abstracts): ~$0.02
- Stage 5 (gpt-5.4-nano, ~8 papers): ~$0.05–0.10
- eval_02_llm + eval_05_llm: ~$0.12

Total: well under $0.20 per end-to-end run. A $5 prepaid card runs the
whole workshop ~25 times.

## Pipeline overview

```
Stage 1 search             PubMed esearch + efetch → pmids.json
Stage 2 screen             abstracts → include/exclude verdict + rationale
Stage 3 download fulltext  PMCID → OA PDF / JATS XML / metadata fallback
Stage 4 pdf to text        PDF + XML + metadata → uniform .md
Stage 5 extract            .md + schema → per-paper extraction JSON
Stage 6 table              flatten per (paper × animal_arm) → CSV
```

## License

MIT — see `LICENSE`.

## Provenance

This workshop bundle is derived from the [`docs/exercise/mAbs/track_B`
directory](https://github.com/jayprimer/ar-bic-2026/tree/main/docs/exercise/mAbs/track_B)
of the `ar-bic-2026` repo. The canonical reference run archived under
`reference_outputs/` was produced May 2026 against a 2025–2026 PubMed
query.
