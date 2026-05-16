# ar-bic-2026 workshop — mAbs animal-study pipeline

You'll build a six-stage pipeline that turns a PubMed query into a
structured CSV of monoclonal-antibody (mAb) animal-study findings.
You write each stage with help from Colab's built-in **Gemini** panel.

## What each stage does

| File | What you implement | Open in Colab |
|---|---|---|
| `stage_1.ipynb` | PubMed esearch + efetch — query → metadata | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jayprimer/ar-bic-2026-workshop/blob/main/stage_1.ipynb) |
| `stage_2.ipynb` | Screen abstracts include / exclude (OpenAI or regex fallback) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jayprimer/ar-bic-2026-workshop/blob/main/stage_2.ipynb) |
| `stage_3.ipynb` | Download OA fulltext (PDF / JATS XML / metadata fallback) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jayprimer/ar-bic-2026-workshop/blob/main/stage_3.ipynb) |
| `stage_4.ipynb` | Convert PDF / XML / metadata → uniform Markdown | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jayprimer/ar-bic-2026-workshop/blob/main/stage_4.ipynb) |
| `stage_5.ipynb` | LLM-extract structured JSON matching the contract | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jayprimer/ar-bic-2026-workshop/blob/main/stage_5.ipynb) |
| `stage_6.ipynb` | Flatten to a CSV — one row per (paper × animal_arm) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jayprimer/ar-bic-2026-workshop/blob/main/stage_6.ipynb) |

Each notebook is **standalone**: it already runs every stage *before*
the one you're writing. You only write Stage N; everything earlier is
pre-built so you can focus.

## Prerequisites

- A Google account (for Colab).
- An OpenAI API key (for Stages 2, 5, and a few LLM evals). About
  **$0.20** of credits covers a full end-to-end run.

## How a stage works

1. Click the "Open in Colab" badge for the stage you're on.
2. In Colab Secrets (sidebar, key icon), add a secret named
   `OPENAI_API_KEY` and toggle "Notebook access" on.
3. Run cells from the top. Everything before "## Stage N" sets up the
   environment and runs earlier stages — every cell should succeed.
4. Read the **"### Your task — write Stage N"** cell. The cell
   immediately below it is the prompt for Gemini, nothing else.
5. Open Colab's **Gemini** panel (sparkle icon, top-right of the
   toolbar). On the prompt cell, click the cell menu (three dots) →
   *Copy cell content*, then paste into Gemini's chat box.
6. Review the code Gemini gives you. Paste it into the empty code
   cell directly below the prompt. Run it.
7. Run the eval cells below. If they pass, you're done with this
   stage; if they fail, iterate with Gemini (paste the failure
   message back into the chat).

## Tips

- The eval cells are your safety net — run them after every change.
- Gemini sometimes hallucinates API shapes (e.g. invented OpenAI
  parameters, wrong NCBI endpoint paths). If a stage fails with an
  obscure error, paste the traceback back into Gemini.
- Stage 5 caches per-paper extractions to disk, so re-running won't
  re-bill the OpenAI calls already made.
- Need a clean rerun? `!rm -rf stage_*/data stage_*/eval` from a cell.

## Files

```
stage_1.ipynb   stage_2.ipynb   stage_3.ipynb
stage_4.ipynb   stage_5.ipynb   stage_6.ipynb
README.md
```

Nothing else; everything you need is inside the notebooks.
