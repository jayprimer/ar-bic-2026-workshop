# AR-BIC 2026 Pre-Conference Workshop

Hands-on companion repo for the workshop. The morning session covers
the shape of AI work — **input → AI → output → eval**, run as a loop,
not a pipeline — and the eval hierarchy that makes the loop converge:
**script** (deterministic, preferred) → **itemized T/F** → **rubric**
(last resort). This repo is the afternoon: you build a worked example
that uses that loop end-to-end.

## The worked example

You'll build a six-stage pipeline that turns a PubMed query into a
structured CSV. The example domain — monoclonal-antibody (mAb)
animal-study findings — is one realization of a *general* pattern.
The same shape (script + LLM stages, each with a paired eval) carries
straight to data analysis and manuscript writing.

Each stage has the same skeleton:

```
input -> [script | LLM] -> output -> eval -> (feedback to next input)
```

Some stages are deterministic (script), some are LLM-driven. Every
stage is paired with the highest level of eval that fits:

| # | Stage | Work | Eval(s) |
|---|---|---|---|
| 1 | Search | script (PubMed esearch + efetch) | script + LLM T/F |
| 2 | Screen | LLM (include/exclude vs criteria) | script + generate-then-verify |
| 3 | Fetch  | script (OA PDF / XML / metadata fallback) | script |
| 4 | Convert | script (PDF/XML/JSON → markdown) | script (size + abstract round-trip) |
| 5 | Extract | LLM (schema-guided structured JSON) | script + generate-then-verify |
| 6 | Table | script (flatten to CSV) | script (row count + cross-tab) |

## Files

### Starter notebooks (one per stage)

Each `stage_N.ipynb` ships every stage *before* N pre-built. Your job
is to write Stage N with Gemini's help, then run the evals to validate.

| File | What you implement | Open in Colab |
|---|---|---|
| `stage_1.ipynb` | Search — PubMed query → records | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jayprimer/ar-bic-2026-workshop/blob/main/stage_1.ipynb) |
| `stage_2.ipynb` | Screen — records + criteria → verdicts | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jayprimer/ar-bic-2026-workshop/blob/main/stage_2.ipynb) |
| `stage_3.ipynb` | Fetch — included PMIDs → OA fulltext | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jayprimer/ar-bic-2026-workshop/blob/main/stage_3.ipynb) |
| `stage_4.ipynb` | Convert — PDF / XML / metadata → uniform markdown | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jayprimer/ar-bic-2026-workshop/blob/main/stage_4.ipynb) |
| `stage_5.ipynb` | Extract — text + schema → structured JSON | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jayprimer/ar-bic-2026-workshop/blob/main/stage_5.ipynb) |
| `stage_6.ipynb` | Table — JSONs → flat CSV | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jayprimer/ar-bic-2026-workshop/blob/main/stage_6.ipynb) |

### Reference notebook

| File | Description | Open in Colab |
|---|---|---|
| `mabs_pipeline.ipynb` | The complete six-stage pipeline + every eval, end-to-end. Use as a reference if you get stuck, or run it after the session for the full experience. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jayprimer/ar-bic-2026-workshop/blob/main/mabs_pipeline.ipynb) |

## Prerequisites

- A Google account (for Colab).
- An OpenAI API key (for Stages 2, 5, and the LLM evals). About
  **$0.20** of credits covers a full end-to-end run.

## How a stage works

1. Click the "Open in Colab" badge for the stage you're on.
2. In Colab **Secrets** (sidebar, key icon), add `OPENAI_API_KEY` and
   toggle "Notebook access" on.
3. Run cells from the top. Everything before "## Stage N" sets up the
   environment and runs the earlier stages — every cell should pass.
4. Read the **"### Your task — write Stage N"** cell. The cell
   immediately below it is the prompt for Gemini, by itself, so you
   can copy the whole cell.
5. Open Colab's **Gemini** panel (sparkle icon, top-right). On the
   prompt cell, click the cell menu (⋮) → *Copy cell content*, then
   paste into Gemini's chat box.
6. Review the code Gemini gives you. Paste it into the empty code
   cell directly below the prompt. Run it.
7. Run the **eval cells** below. If they pass, you're done with this
   stage; if not, iterate with Gemini — paste failure messages back
   into the chat.

## Tips

- Eval cells are your safety net. Run them after every change.
- Gemini sometimes hallucinates API shapes (made-up parameters,
  wrong endpoint paths). If a stage fails with an obscure error,
  paste the traceback back into the chat.
- Stage 5 caches per-paper extractions, so re-running won't re-bill
  the OpenAI calls already made.
- Clean rerun: `!rm -rf stage_*/data stage_*/eval` from a cell.
- Stuck? Open `mabs_pipeline.ipynb` and read how the reference
  implementation does it.

## What carries over

The mAbs example is just one realization. The pattern — decompose
a fuzzy task into stages, choose script vs LLM per stage, pair each
stage with the highest-level eval that fits — applies the same way
to data analysis and manuscript writing. Take the eval-decomposition
move with you; it's the part that pays off all year.
