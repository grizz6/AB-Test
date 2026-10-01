"""Call an LLM hosted on GitHub Models.

Auth uses a GitHub token read from the GITHUB_TOKEN environment variable. Inside
GitHub Actions the built-in token works when the workflow grants `models: read`,
so no separate API key exists to leak. Locally, use a fine-grained personal access
token with the "Models" permission, kept in a git-ignored .env file.

Smoke test:  python -m src.llm "Say hi"
"""

from __future__ import annotations

import os
import sys

import requests

from src.config import load_config

API_VERSION = "2022-11-28"
TIMEOUT_SECONDS = 60


class LLMError(RuntimeError):
    pass


def _token() -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise LLMError("GITHUB_TOKEN is not set. See .env.example.")
    return token


def _headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": API_VERSION,
        "Content-Type": "application/json",
    }


def build_payload(messages: list[dict[str, str]], llm_cfg: dict) -> dict:
    return {
        "model": llm_cfg["model"],
        "messages": messages,
        "temperature": llm_cfg.get("temperature", 0.0),
        "max_tokens": llm_cfg.get("max_tokens", 500),
    }


def chat(messages: list[dict[str, str]], llm_cfg: dict | None = None) -> str:
    """Send chat messages and return the reply text."""
    llm_cfg = llm_cfg or load_config()["llm"]
    url = f"{llm_cfg['endpoint'].rstrip('/')}/chat/completions"
    resp = requests.post(
        url,
        headers=_headers(_token()),
        json=build_payload(messages, llm_cfg),
        timeout=TIMEOUT_SECONDS,
    )
    if resp.status_code != 200:
        raise LLMError(f"GitHub Models returned {resp.status_code}: {resp.text[:500]}")
    try:
        data = resp.json()
    except ValueError as exc:
        raise LLMError(
            f"GitHub Models returned 200 but the body is not valid JSON "
            f"(Content-Type: {resp.headers.get('Content-Type')!r}, "
            f"body: {resp.text[:500]!r})"
        ) from exc
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"GitHub Models returned an unexpected response: {str(data)[:500]}") from exc


def list_models() -> list[str]:
    """Model IDs available on GitHub Models (useful when a configured model is retired)."""
    resp = requests.get(
        "https://models.github.ai/catalog/models",
        headers=_headers(_token()),
        timeout=TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    return sorted(m["id"] for m in resp.json())


def _print_available_models() -> None:
    try:
        print("Available models:", ", ".join(list_models()), file=sys.stderr)
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        print(f"Could not list models: {exc}", file=sys.stderr)


def main() -> None:
    prompt = " ".join(sys.argv[1:]) or "Say hi"
    try:
        print(chat([{"role": "user", "content": prompt}]))
    except LLMError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        _print_available_models()
        sys.exit(1)


if __name__ == "__main__":
    main()
