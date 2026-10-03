# Journal

## Day 1: Setup

- Chose a fully cloud, $0 stack: GitHub Actions + Gemini API free tier (LLM), Supabase
  pgvector, Hugging Face Spaces. No local LLM; no credit card anywhere.
- First tried GitHub Models, but CI got a plain-text "OK" instead of a reply: GitHub retired
  GitHub Models on 2026-07-30. Lesson: verify a service is still live before building on it.
  Switched to Gemini; its key lives only in the GEMINI_API_KEY repo secret.
- Wrote `.gitignore` first (`.env`, `data/`, `mlruns/`, `*.db`), plus `.env.example`.
- CI: ruff (lint + format), pytest, gitleaks secret scan on full history, and an LLM
  smoke test ("say hi").
- All settings in `config.yaml` so later experiments change config, not code.

## Day 2: Download filings

- `src/download.py`: ticker -> CIK from `company_tickers.json`, latest original 10-K from
  `data.sec.gov/submissions` (skips 10-K/A amendments), HTML saved to `data/raw/`, plus a
  `manifest.json` with each file's source URL and accession number for citations later.
- SEC rules: `User-Agent` from the `SEC_USER_AGENT` secret, requests spaced >= 0.2 s apart,
  retries with backoff on 429/5xx only.
- Runs in the cloud: `.github/workflows/pipeline.yml` downloads the filings in GitHub Actions
  and keeps them as the `raw-filings` artifact (data never goes into git).
- Gemini `gemini-2.5-flash` is closed to new users; pinned `gemini-3.8-flash` (pinned, not the
  `-latest` alias, so evaluation runs stay comparable).
- First real run: 6/10 downloaded, then XOM failed. Exxon redomiciled to a new Texas holding
  company on 2026-07-01; the "XOM" ticker now maps to the new CIK, which has no 10-K yet.
  Added `cik_overrides` in config.yaml (XOM -> 34088, where the 10-Ks are).
- Gemini answered 503 "high demand" once; the client now retries 429/500/503 with backoff
  (2, 4, 8 s) and fails fast on other errors.

## Day 3: Parse + chunk

- `src/parse.py`: HTML -> text (one line per block element; hidden inline-XBRL header and
  `display:none` blocks dropped), then find Item 1A by heading lines only. The table of
  contents and "see Item 1A" cross-references also match, so every start is paired with the
  next end heading (Item 1B / 1C / 2 or "Unresolved Staff Comments") and the longest span
  wins. Page numbers and "Table of Contents" running headers are removed.
- Sanity check: a section under 1,500 or over 80,000 words fails the pipeline, which prints
  each company's word count and first/last words so a wrong span is obvious in the log.
- `src/chunk.py`: 400-word windows, 50-word overlap, IDs like `TSLA_1A_0012`; each chunk keeps
  company, source URL and filing date for citations.

## Day 4: Embed + store

- `all-MiniLM-L6-v2` (384 dims) with normalized vectors, stored in Supabase Postgres with
  pgvector, HNSW index on cosine distance.
- Rows are keyed by `(index_name, id)`: re-indexing replaces one index in a single
  transaction, PR runs write to `ci`, and later chunking experiments get their own index
  instead of overwriting `main`.
- PyTorch is large, so embedding deps live in `requirements-index.txt` (CPU wheels) and only
  the pipeline installs them; the fast CI job stays light.
- Supabase's direct host is IPv6-only and GitHub runners have no IPv6, so the connection uses
  the session pooler URL.
