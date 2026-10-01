# Journal

## Day 1: Setup

- Chose a fully cloud, $0 stack: GitHub Actions + GitHub Models (LLM), Supabase pgvector,
  Hugging Face Spaces. No local LLM; no credit card anywhere.
- GitHub Models is called with the built-in Actions token (`models: read`), so there is no
  LLM API key to leak.
- Wrote `.gitignore` first (`.env`, `data/`, `mlruns/`, `*.db`), plus `.env.example`.
- CI: ruff (lint + format), pytest, gitleaks secret scan on full history, and an LLM
  smoke test ("say hi").
- All settings in `config.yaml` so later experiments change config, not code.
