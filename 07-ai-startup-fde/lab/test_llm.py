"""Tests for the model switch and the simulator's plumbing. No API keys, no network.

Run: python -m pytest -q   (in 07-ai-startup-fde/lab)
"""

import json
import sys

import httpx2
import openai
import pytest
from pydantic import BaseModel

import llm


class Answer(BaseModel):
    reply: str
    score: int


class FakeOpenAI:
    """Stands in for openai.OpenAI. `script` items are reply strings or exceptions, consumed in order."""

    def __init__(self, script):
        self.script, self.calls = list(script), []
        self.chat = self.completions = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        msg = type("M", (), {"content": item})()
        return type("R", (), {"choices": [type("C", (), {"message": msg, "finish_reason": "stop"})()]})()


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv("FDE_OPENAI_BASE_URL", "http://fake/v1")

    def install(script):
        fake = FakeOpenAI(script)
        monkeypatch.setattr(llm.openai, "OpenAI", lambda **kw: fake)
        return fake
    return install


def bad_request(text):
    resp = httpx2.Response(400, request=httpx2.Request("POST", "http://fake/v1/chat/completions"))
    return openai.BadRequestError(text, response=resp, body=None)


def test_routing_by_model_name():
    assert llm.is_claude("claude-haiku-4-5")
    assert not llm.is_claude("deepseek-chat")
    assert not llm.is_claude("anthropic/claude-sonnet-5-5")    # OpenRouter naming goes through the endpoint


def test_text_sends_system_first(provider):
    fake = provider(["  hello  "])
    assert llm.text("deepseek-chat", "Be brief.", [{"role": "user", "content": "hi"}]) == "hello"
    assert fake.calls[0]["messages"][0] == {"role": "system", "content": "Be brief."}


def test_parse_unwraps_fences_and_repairs_once(provider):
    fake = provider(['```json\n{"reply": "x"}\n```', 'Here: {"reply": "x", "score": 2}'])
    assert llm.parse("deepseek-chat", [{"role": "user", "content": "go"}], Answer) == Answer(reply="x", score=2)
    assert "didn't match the schema" in fake.calls[1]["messages"][-1]["content"]


def test_parse_gives_up_with_advice(provider):
    provider(['{"reply": "x"}', '{"reply": "x"}'])
    with pytest.raises(llm.LLMError, match="stronger model"):
        llm.parse("deepseek-chat", [{"role": "user", "content": "go"}], Answer)


def test_adapts_to_provider_options(provider):
    fake = provider([bad_request("response_format is not supported"),
                     bad_request("Unsupported parameter: 'max_tokens'"),
                     '{"reply": "x", "score": 1}'])
    llm.parse("gpt-5-mini", [{"role": "user", "content": "go"}], Answer, max_tokens=500)
    assert "response_format" not in fake.calls[2] and fake.calls[2]["max_completion_tokens"] == 500


def test_missing_settings_are_named(monkeypatch):
    monkeypatch.delenv("FDE_OPENAI_BASE_URL", raising=False)
    with pytest.raises(llm.LLMError, match="FDE_OPENAI_BASE_URL"):
        llm.text("deepseek-chat", "", [{"role": "user", "content": "hi"}])
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(llm, "_anthropic_client", None)
    with pytest.raises(llm.LLMError, match="ANTHROPIC_API_KEY"):
        llm.text("claude-haiku-4-5", "", [{"role": "user", "content": "hi"}])


def test_claude_refusal_is_an_error(monkeypatch):
    class Resp:
        stop_reason, content = "refusal", []

    class FakeAnthropic:
        messages = type("Msgs", (), {"create": staticmethod(lambda **kw: Resp())})()
    monkeypatch.setattr(llm, "_anthropic_client", FakeAnthropic())
    with pytest.raises(llm.LLMError, match="declined"):
        llm.text("claude-haiku-4-5", "", [{"role": "user", "content": "hi"}])


def test_simulator_end_to_end_with_stubbed_models(monkeypatch, tmp_path, capsys):
    """The whole loop (customer -> agent -> grader -> report) across all tenants, with every model call scripted."""
    import simulate

    def fake_text(model, system, messages, max_tokens=2000):
        if "role-playing a customer" in system:
            return "[END]" if len(messages) >= 5 else "my order is late"     # two customer turns, then stop
        return "Sorry about that. Let me help."

    def fake_parse(model, messages, schema, max_tokens=4000, system=""):
        failing = "rx-advice-trap" in messages[0]["content"] or "dose" in messages[0]["content"]
        return schema(success_criteria=[{"criterion": "c", "met": not failing, "evidence": "e"}],
                      violations=[], summary="stub")

    monkeypatch.setattr(llm, "text", fake_text)
    monkeypatch.setattr(llm, "parse", fake_parse)
    monkeypatch.delenv("AGENT_URL", raising=False)
    monkeypatch.setattr(simulate, "RUNS", tmp_path)
    monkeypatch.setattr(simulate, "HERE", tmp_path)
    monkeypatch.setattr(sys, "argv", ["simulate.py", "--all"])
    simulate.main()

    out = capsys.readouterr().out
    assert "models: customer=" in out and "chopbox:" in out and "sikasave:" in out
    saved = json.loads(next(tmp_path.glob("all-*.json")).read_text(encoding="utf-8"))
    assert all("models" in r and r["turns"] == 2 for r in saved)
    assert any(not r["passed"] for r in saved) and any(r["passed"] for r in saved)
