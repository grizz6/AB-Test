import pytest

from src import llm

CFG = {
    "endpoint": "https://example.test/inference",
    "model": "some/model",
    "temperature": 0.0,
    "max_tokens": 50,
}


class FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = {"Content-Type": "application/json"}

    def json(self):
        if self._payload is None:  # same as requests on an empty or non-JSON body
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return self._payload


def test_missing_token_raises(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(llm.LLMError, match="GITHUB_TOKEN"):
        llm.chat([{"role": "user", "content": "hi"}], CFG)


def test_chat_sends_expected_request(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    seen = {}

    def fake_post(url, headers, json, timeout):
        seen.update(url=url, headers=headers, json=json)
        return FakeResponse(200, {"choices": [{"message": {"content": " hi \n"}}]})

    monkeypatch.setattr(llm.requests, "post", fake_post)
    assert llm.chat([{"role": "user", "content": "Say hi"}], CFG) == "hi"
    assert seen["url"] == "https://example.test/inference/chat/completions"
    assert seen["headers"]["Authorization"] == "Bearer test-token"
    assert seen["json"]["model"] == "some/model"
    assert seen["json"]["messages"][0]["content"] == "Say hi"


def test_chat_error_status_raises(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setattr(
        llm.requests, "post", lambda *a, **k: FakeResponse(429, text="rate limited")
    )
    with pytest.raises(llm.LLMError, match="429"):
        llm.chat([{"role": "user", "content": "hi"}], CFG)


def test_empty_200_body_raises_clear_error(monkeypatch):
    # Seen in CI: HTTP 200 with an empty body. Must fail with a readable message.
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: FakeResponse(200, None, text=""))
    with pytest.raises(llm.LLMError, match="not valid JSON"):
        llm.chat([{"role": "user", "content": "hi"}], CFG)


def test_200_without_choices_raises_clear_error(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setattr(
        llm.requests, "post", lambda *a, **k: FakeResponse(200, {"error": "nope"}, text="{}")
    )
    with pytest.raises(llm.LLMError, match="unexpected response"):
        llm.chat([{"role": "user", "content": "hi"}], CFG)
