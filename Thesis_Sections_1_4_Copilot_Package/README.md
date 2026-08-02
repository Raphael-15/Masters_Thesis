# Thesis Sections 1–4 — Copilot Package

This package contains Chapters 1–4 of the thesis in formats designed for GitHub repositories and LLM coding assistants.

## Folder structure

```text
canonical_tex/                 Exact LaTeX chapter sources; authoritative
llm_markdown/                  LLM-friendly Markdown wrappers with exact LaTeX embedded
plain_text_search/             Derived text files for fast searching
metadata/thesis_manifest.json  Project-level machine-readable context
metadata/section_index.json    Headings, labels, and source-line navigation
references.bib                 Citation database
ALL_SECTIONS_1_TO_4.tex        Consolidated canonical LaTeX source
ALL_SECTIONS_1_TO_4_FOR_LLM.md Consolidated LLM context file
COPILOT_START_PROMPT.txt        Ready-to-paste instruction for Copilot Chat
```

## Recommended Copilot workflow

Open `llm_markdown/00_COPILOT_CONTEXT.md` first, then attach only the chapter files needed for the current task. Use `canonical_tex/` when editing LaTeX or checking equations and labels.

The Markdown and plain-text versions are supporting views. The canonical LaTeX source remains the authority.
