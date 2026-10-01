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

    def json(self):
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
