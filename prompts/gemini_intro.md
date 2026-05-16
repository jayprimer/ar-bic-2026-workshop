# Using Colab's Gemini assistant in this workshop

Each stage notebook ships a **spec card** (Section 2) and a **gotchas
list** (Section 3). Your job is to drive Gemini to produce a working
script that meets the spec without falling into the gotchas.

## Where Gemini lives

Top-right corner of the Colab tab: a sparkles icon labelled **Gemini**.
Clicking it opens a side panel with a chat box. You can also press
`Ctrl+L` (or `Cmd+L` on Mac) to focus the chat.

A useful Colab habit: when Gemini suggests code, click the **Insert**
button to drop it into the currently-selected cell rather than the cell
Gemini guesses.

## Workflow per stage

1. **Run the bootstrap + setup cells** at the top of the notebook.
   Don't skip these — they `git clone` the repo, install dependencies,
   and bridge your API key.
2. **Read the spec card** carefully. Then paste the WHOLE spec (the
   `\`\`\`` block) as your first prompt to Gemini.
3. **Add the gotchas inline** when relevant. If Gemini's first draft
   ignores `itertext()` or the `/deprecated/` URL rewrite, paste the
   relevant gotcha bullet as a follow-up.
4. **Run the implementation cell**, fix what breaks, iterate.
5. **Run the verification cell.** If it passes, run the eval grader.
6. **Stuck?** Use the "Skip this stage" cell at the bottom to copy the
   reference run's output into place and move on. You can come back to
   the stage later.

## Prompt patterns that work

### Spec-first

> Here is the spec for a Python script I need to write. Use only the
> standard library. Output the entire script as a single code block.
>
> [paste spec card]

### Add a gotcha after the first draft

> Your script uses `.text` on `<ArticleTitle>`. PubMed inlines `<i>`,
> `<sub>`, and `<sup>` children inside titles, and `.text` will only
> return the prefix before the first child. Rewrite the title and
> abstract parsers to use `itertext()` joined together.

### Counter-prompt for hallucinated APIs

> You're using `requests` and `Bio.Entrez`. The workshop constraint
> is **standard library only** — switch to `urllib.request` and
> `xml.etree.ElementTree`.

### When Gemini is too clever

> Don't refactor into classes. A single top-to-bottom script is the
> deliverable shape. Inline helpers as functions if needed.

## When NOT to use Gemini

- **Reading error messages.** Read them yourself first. Gemini will
  guess; the traceback already tells you the answer.
- **Reading the spec.** The spec is short and concrete — read it
  before prompting so you can tell when Gemini drifts.
- **API keys, secrets, anything sensitive.** Don't paste them.

## Useful prompts to keep handy

| Situation | Prompt |
|---|---|
| Stage drift | "Re-read the spec card I pasted earlier. Are you still satisfying every numbered requirement?" |
| Verbose output | "Just output the script. No explanation, no markdown commentary." |
| Mystery import | "I'm getting `ModuleNotFoundError: No module named 'X'`. The workshop uses only the standard library and the `openai` package. Rewrite without X." |
| Won't stop refactoring | "Don't change the file structure. Only fix the specific bug I described." |
