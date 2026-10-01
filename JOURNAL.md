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
