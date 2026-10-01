# Filings Q&A

Ask questions about the **Risk Factors** section of 10 companies' annual reports (10-K
filings) and get answers with citations, e.g. *"What does Tesla say about supply chain risk?"*

A retrieval-augmented generation (RAG) system built as an MLOps project: tracked experiments,
an evaluation test set, CI that blocks changes when retrieval quality drops, a containerized
app, and monitoring. Runs entirely on free cloud services, with no credit card and no local LLM.

> **Status:** Day 2 of 10 (download filings). See the roadmap below.

## Cloud stack (all free tiers)

| Piece | Service |
|---|---|
| Code, CI, eval gate, container registry | GitHub, GitHub Actions, GHCR |
| LLM | Google Gemini API, free tier (`gemini-3.8-flash`) |
| Vector store + question log | Supabase Postgres with pgvector |
| App hosting (API, UI, dashboard) | Hugging Face Spaces |
| Data source | SEC EDGAR (public, no key) |

## Secrets

No secret is ever committed. `.env` is git-ignored and CI scans every push with gitleaks.
Secrets live in **repo Settings → Secrets and variables → Actions**:

| Secret | Used for | Needed from |
|---|---|---|
| `GEMINI_API_KEY` | LLM calls (Google AI Studio key) | Day 1 |
| `SEC_USER_AGENT` | SEC requires `Name email` on every request | Day 2 |
| `SUPABASE_DB_URL` | Postgres connection string | Day 4 |
| `HF_TOKEN` | Deploying to Hugging Face Spaces | Day 9 |

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # fill in values; never commit .env
ruff check . && pytest -q
python -m src.llm "Say hi"   # needs GEMINI_API_KEY in .env
python -m src.download       # needs SEC_USER_AGENT in .env; writes data/raw/
```

## Roadmap

| Day | What | Status |
|---|---|---|
| 1 | Setup, CI (ruff, pytest, gitleaks), LLM smoke test | done |
| 2 | Download 10 filings from SEC EDGAR (`src/download.py`, pipeline workflow) | in progress |
| 3 | Parse "Item 1A. Risk Factors" + chunk + tests | |
| 4 | Embed + store in Supabase pgvector | |
| 5 | Retrieve + answer with citations (v1.0) | |
| 6 | 50-question test set | |
| 7 | Evaluation + MLflow experiments | |
| 8 | CI eval gate (blocks quality drops) | |
| 9 | FastAPI + Streamlit + Docker, deployed to Spaces | |
| 10 | Monitoring dashboard + README + demo | |
