"""The one place the simulator talks to a model.

Everything else calls `parse(...)`, so tests can swap in a scripted fake with `set_backend`, and a missing
API key shows up as one clear, friendly error instead of a stack trace.

Models named `claude-*` go to Anthropic. Any other model name goes to an OpenAI-compatible endpoint set by
FDE_OPENAI_BASE_URL (+ FDE_OPENAI_API_KEY), which covers OpenRouter, DeepSeek, Groq, Gemini, OpenAI and a local Ollama.
"""

import json
import os
import re
from typing import Callable, Type, TypeVar

import anthropic
import openai
from pydantic import BaseModel, ValidationError

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


def is_claude(model: str) -> bool:
    return model.startswith("claude-")


def _has_credentials(model: str) -> bool:
    if is_claude(model):
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    return bool(os.environ.get("FDE_OPENAI_BASE_URL"))    # a local Ollama needs no key


def configured() -> bool:
    return _backend is not None or all(_has_credentials(m) for m in (CHAT_MODEL, JUDGE_MODEL))


def _real(model: str, system: str, messages: list[dict], schema: Type[T], max_tokens: int) -> T:
    return (_anthropic if is_claude(model) else _openai_compatible)(model, system, messages, schema, max_tokens)


def _anthropic(model: str, system: str, messages: list[dict], schema: Type[T], max_tokens: int) -> T:
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


_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.S)


def _json_text(text: str) -> str:
    """Cheaper models often wrap JSON in ``` fences or add a sentence around it; keep only the object."""
    m = _FENCE.match(text)
    if m:
        text = m.group(1)
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if start != -1 and end > start else text


def _openai_compatible(model: str, system: str, messages: list[dict], schema: Type[T], max_tokens: int) -> T:
    base_url = os.environ.get("FDE_OPENAI_BASE_URL")
    if not base_url:
        raise LLMUnavailable(
            f"'{model}' isn't a Claude model, so it needs an OpenAI-compatible endpoint. Set FDE_OPENAI_BASE_URL "
            "(and FDE_OPENAI_API_KEY) in console/.env, then `docker compose up -d sim`."
        )
    client = openai.OpenAI(base_url=base_url, api_key=os.environ.get("FDE_OPENAI_API_KEY") or "not-needed")
    # No portable structured-output feature across providers: put the schema in the prompt, validate, repair once.
    instructions = (f"{system}\n\nRespond with a single JSON object and nothing else. It must match this JSON Schema:\n"
                    f"{json.dumps(schema.model_json_schema())}")
    convo = [{"role": "system", "content": instructions}, *messages]
    options = {"max_tokens": max_tokens, "response_format": {"type": "json_object"}}

    for attempt in range(2):
        text = _openai_call(client, model, convo, options)
        try:
            return schema.model_validate_json(_json_text(text))
        except ValidationError as e:
            if attempt == 1:
                raise LLMUnavailable(f"'{model}' twice returned JSON that didn't fit the expected shape. "
                                     "Smaller models struggle with long structured answers; try a stronger one for this role.")
            convo = [*convo, {"role": "assistant", "content": text},
                     {"role": "user", "content": f"That JSON didn't match the schema ({e.error_count()} errors, first: "
                                                 f"{e.errors()[0]['msg']} at {e.errors()[0]['loc']}). "
                                                 "Reply with only the corrected JSON object."}]
    raise AssertionError("unreachable")


def _openai_call(client: openai.OpenAI, model: str, convo: list[dict], options: dict) -> str:
    """One request, adapting to what this provider accepts (JSON mode and the token-limit parameter vary)."""
    for _ in range(3):
        try:
            response = client.chat.completions.create(model=model, messages=convo, **options)
        except openai.BadRequestError as e:
            msg = str(e).lower()
            if "response_format" in msg and "response_format" in options:
                options = {k: v for k, v in options.items() if k != "response_format"}
                continue
            if "max_tokens" in msg and "max_tokens" in options:     # newer OpenAI models want max_completion_tokens
                options = {**{k: v for k, v in options.items() if k != "max_tokens"},
                           "max_completion_tokens": options["max_tokens"]}
                continue
            raise LLMUnavailable(f"The provider rejected the request for '{model}': {e.message}")
        except openai.AuthenticationError:
            raise LLMUnavailable("The provider rejected FDE_OPENAI_API_KEY (401). Check the key.")
        except openai.NotFoundError:
            raise LLMUnavailable(f"The provider doesn't know the model '{model}'. Check the exact model name in its docs.")
        except openai.RateLimitError:
            raise LLMUnavailable("Rate limited by the provider. Wait a few seconds and try again.")
        except openai.APIConnectionError:
            raise LLMUnavailable(f"Could not reach {client.base_url}. Check FDE_OPENAI_BASE_URL and your network.")
        except openai.APIStatusError as e:
            raise LLMUnavailable(f"The provider returned {e.status_code}: {e.message}")
        choice = response.choices[0]
        if choice.finish_reason == "length":
            raise LLMUnavailable("The model's answer was cut off. Try again, or use a model with a larger output limit.")
        return choice.message.content or ""
    raise LLMUnavailable(f"The provider kept rejecting the request options for '{model}'.")


def parse(model: str, system: str, messages: list[dict], schema: Type[T], max_tokens: int = 8000) -> T:
    return (_backend or _real)(model, system, messages, schema, max_tokens)
