"""The OpenAI-compatible path (non-Claude models), driven by a fake provider: no network, no keys."""

import httpx2
import openai
import pytest
from pydantic import BaseModel

from sim import llm


class Answer(BaseModel):
    reply: str
    score: int


class FakeProvider:
    """Stands in for openai.OpenAI. `script` is a list of replies (str) or exceptions, consumed in order."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []
        self.base_url = "http://fake/v1/"
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        msg = type("M", (), {"content": item})()
        choice = type("C", (), {"message": msg, "finish_reason": "stop"})()
        return type("R", (), {"choices": [choice]})()


def bad_request(text):
    resp = httpx2.Response(400, request=httpx2.Request("POST", "http://fake/v1/chat/completions"))
    return openai.BadRequestError(text, response=resp, body=None)


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv("FDE_OPENAI_BASE_URL", "http://fake/v1")
    holder = {}

    def install(script):
        fake = FakeProvider(script)
        monkeypatch.setattr(llm.openai, "OpenAI", lambda **kw: fake)
        holder["fake"] = fake
        return fake
    return install


def ask(model="deepseek-chat"):
    return llm.parse(model, "You are terse.", [{"role": "user", "content": "hi"}], Answer, 1000)


def test_claude_names_go_to_anthropic_everything_else_to_the_endpoint():
    assert llm.is_claude("claude-sonnet-5-5")
    assert not llm.is_claude("deepseek-chat")
    assert not llm.is_claude("anthropic/claude-sonnet-5-5")   # an OpenRouter name: goes through the endpoint


def test_plain_json_is_parsed_and_schema_is_in_the_prompt(provider):
    fake = provider(['{"reply": "hello", "score": 4}'])
    assert ask() == Answer(reply="hello", score=4)
    system = fake.calls[0]["messages"][0]
    assert system["role"] == "system" and '"score"' in system["content"]
    assert fake.calls[0]["response_format"] == {"type": "json_object"}


def test_fenced_or_chatty_json_is_unwrapped(provider):
    provider(['Sure! Here it is:\n```json\n{"reply": "ok", "score": 2}\n```'])
    assert ask().score == 2


def test_wrong_shape_gets_one_repair_attempt(provider):
    fake = provider(['{"reply": "ok"}', '{"reply": "ok", "score": 3}'])
    assert ask().score == 3
    assert "didn't match the schema" in fake.calls[1]["messages"][-1]["content"]


def test_wrong_shape_twice_is_a_friendly_error(provider):
    provider(['{"reply": "ok"}', '{"nope": 1}'])
    with pytest.raises(llm.LLMUnavailable, match="stronger"):
        ask()


def test_provider_without_json_mode_is_retried_without_it(provider):
    fake = provider([bad_request("response_format json_object is not supported"), '{"reply": "x", "score": 1}'])
    assert ask().reply == "x"
    assert "response_format" not in fake.calls[1]


def test_models_that_want_max_completion_tokens(provider):
    fake = provider([bad_request("Unsupported parameter: 'max_tokens'. Use 'max_completion_tokens'."),
                     '{"reply": "x", "score": 1}'])
    ask("gpt-5-mini")
    assert fake.calls[1]["max_completion_tokens"] == 1000 and "max_tokens" not in fake.calls[1]


def test_missing_endpoint_names_the_setting(monkeypatch):
    monkeypatch.delenv("FDE_OPENAI_BASE_URL", raising=False)
    with pytest.raises(llm.LLMUnavailable, match="FDE_OPENAI_BASE_URL"):
        ask()


def test_configured_needs_credentials_for_both_roles(monkeypatch):
    monkeypatch.setattr(llm, "CHAT_MODEL", "deepseek-chat")
    monkeypatch.setattr(llm, "JUDGE_MODEL", "claude-opus-5-5")
    monkeypatch.setenv("FDE_OPENAI_BASE_URL", "http://fake/v1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert not llm.configured()          # the judge is still Claude and has no key
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert llm.configured()
