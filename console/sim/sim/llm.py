"""The one place the simulator talks to Claude.

Everything else calls `parse(...)`, so tests can swap in a scripted fake with `set_backend`, and a missing
API key shows up as one clear, friendly error instead of a stack trace.
"""

import os
from typing import Callable, Type, TypeVar

import anthropic
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

# Both default models think before answering, and thinking tokens count against max_tokens, so callers pass generous limits.
# Role-play needs good judgement about *when* to reveal things, so the default is the strongest model.
# Override per environment, e.g. FDE_CHAT_MODEL=claude-sonnet-5-5 to cut cost.
CHAT_MODEL = os.environ.get("FDE_CHAT_MODEL", "claude-opus-5-5")
JUDGE_MODEL = os.environ.get("FDE_JUDGE_MODEL", "claude-opus-5-5")


class LLMUnavailable(Exception):
    """No credentials, a refusal, or the API is down. The message is safe to show the learner."""


Backend = Callable[..., BaseModel]
_backend: Backend | None = None
_client: anthropic.Anthropic | None = None


def set_backend(fn: Backend | None):
    """Tests only: replace the real API call with `fn(model, system, messages, schema, max_tokens)`."""
    global _backend
    _backend = fn


def configured() -> bool:
    return _backend is not None or bool(os.environ.get("ANTHROPIC_API_KEY"))


def _real(model: str, system: str, messages: list[dict], schema: Type[T], max_tokens: int) -> T:
    global _client
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise LLMUnavailable(
            "ANTHROPIC_API_KEY is not set for the simulator. Export it in the shell where you run "
            "`docker compose up`, then restart the sim container (`docker compose up -d sim`)."
        )
    if _client is None:
        _client = anthropic.Anthropic()
    try:
        response = _client.messages.parse(
            model=model, max_tokens=max_tokens, system=system, messages=messages, output_format=schema,
        )
    except anthropic.AuthenticationError:
        raise LLMUnavailable("The Anthropic API rejected ANTHROPIC_API_KEY (401). Check the key.")
    except anthropic.RateLimitError:
        raise LLMUnavailable("Rate limited by the Anthropic API. Wait a few seconds and try again.")
    except anthropic.APIConnectionError:
        raise LLMUnavailable("Could not reach the Anthropic API. Check your network, then try again.")
    except anthropic.APIStatusError as e:
        raise LLMUnavailable(f"The Anthropic API returned {e.status_code}: {e.message}")
    if response.stop_reason == "refusal":
        raise LLMUnavailable("The model declined this turn. Rephrase and try again.")
    if response.stop_reason == "max_tokens" or response.parsed_output is None:
        raise LLMUnavailable("The model's answer was cut off. Try again.")
    return response.parsed_output


def parse(model: str, system: str, messages: list[dict], schema: Type[T], max_tokens: int = 8000) -> T:
    return (_backend or _real)(model, system, messages, schema, max_tokens)
