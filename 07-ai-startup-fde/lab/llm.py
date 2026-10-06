"""The one place this lab talks to a model. Same rules as the Console (console/sim/sim/llm.py):

- model names starting with `claude-` go to Anthropic (ANTHROPIC_API_KEY)
- any other name goes to an OpenAI-compatible endpoint: FDE_OPENAI_BASE_URL (+ FDE_OPENAI_API_KEY),
  which covers OpenRouter, DeepSeek, Groq, Gemini, OpenAI and a local Ollama

Three roles, each set by its own environment variable (defaults in brackets):
  FDE_SIM_CUSTOMER_MODEL  plays the customer             [claude-opus-5-5]  cheap models do fine here
  FDE_SIM_JUDGE_MODEL     grades each transcript         [claude-opus-5-5]  keep this one strong
  FDE_AGENT_MODEL         the naive baseline agent       [claude-opus-5-5]  only when AGENT_URL is unset
"""

import json
import os
import re
from typing import Type, TypeVar

import anthropic
import openai
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

CUSTOMER_MODEL = os.environ.get("FDE_SIM_CUSTOMER_MODEL", "claude-opus-5-5")
JUDGE_MODEL = os.environ.get("FDE_SIM_JUDGE_MODEL", "claude-opus-5-5")
AGENT_MODEL = os.environ.get("FDE_AGENT_MODEL", "claude-opus-5-5")


class LLMError(RuntimeError):
    """A clear, actionable failure: missing settings, a rejected key, a cut-off or unusable answer."""


def is_claude(model: str) -> bool:
    return model.startswith("claude-")


# ---------- Anthropic ----------

_anthropic_client = None


def _anthropic() -> anthropic.Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise LLMError("Claude models need ANTHROPIC_API_KEY. Set it, or pick non-Claude models (see llm.py).")
        _anthropic_client = anthropic.Anthropic()
    return _anthropic_client


def _check_stop(response, model: str):
    if response.stop_reason == "refusal":
        raise LLMError(f"{model} declined this turn.")
    if response.stop_reason == "max_tokens":
        raise LLMError(f"{model}'s answer was cut off (max_tokens).")


# ---------- OpenAI-compatible ----------

_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.S)


def _openai_client() -> openai.OpenAI:
    base_url = os.environ.get("FDE_OPENAI_BASE_URL")
    if not base_url:
        raise LLMError("Non-Claude models need FDE_OPENAI_BASE_URL (and FDE_OPENAI_API_KEY). See llm.py.")
    return openai.OpenAI(base_url=base_url, api_key=os.environ.get("FDE_OPENAI_API_KEY") or "not-needed")


def _openai_call(model: str, messages: list[dict], options: dict) -> str:
    """One request, adapting to what this provider accepts (JSON mode and the token-limit parameter vary)."""
    client = _openai_client()
    for _ in range(3):
        try:
            response = client.chat.completions.create(model=model, messages=messages, **options)
        except openai.BadRequestError as e:
            msg = str(e).lower()
            if "response_format" in msg and "response_format" in options:
                options = {k: v for k, v in options.items() if k != "response_format"}
                continue
            if "max_tokens" in msg and "max_tokens" in options:
                options = {**{k: v for k, v in options.items() if k != "max_tokens"},
                           "max_completion_tokens": options["max_tokens"]}
                continue
            raise LLMError(f"The provider rejected the request for {model}: {e.message}")
        except openai.AuthenticationError:
            raise LLMError("The provider rejected FDE_OPENAI_API_KEY (401).")
        except openai.NotFoundError:
            raise LLMError(f"The provider doesn't know the model '{model}'. Check its model list.")
        except openai.APIError as e:
            raise LLMError(f"Provider error for {model}: {e}")
        choice = response.choices[0]
        if choice.finish_reason == "length":
            raise LLMError(f"{model}'s answer was cut off (max_tokens).")
        return choice.message.content or ""
    raise LLMError(f"The provider kept rejecting the request options for {model}.")


def _json_text(text: str) -> str:
    m = _FENCE.match(text)
    if m:
        text = m.group(1)
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if start != -1 and end > start else text


# ---------- the two calls the lab needs ----------

def text(model: str, system: str, messages: list[dict], max_tokens: int = 2000) -> str:
    """A plain text reply. messages: [{"role": "user"|"assistant", "content": str}, ...]"""
    if is_claude(model):
        response = _anthropic().messages.create(model=model, max_tokens=max_tokens, system=system, messages=messages)
        _check_stop(response, model)
        return "".join(b.text for b in response.content if b.type == "text").strip()
    return _openai_call(model, [{"role": "system", "content": system}, *messages], {"max_tokens": max_tokens}).strip()


def parse(model: str, messages: list[dict], schema: Type[T], max_tokens: int = 4000, system: str = "") -> T:
    """A reply validated against a Pydantic schema."""
    if is_claude(model):
        kwargs = {"system": system} if system else {}
        response = _anthropic().messages.parse(model=model, max_tokens=max_tokens, messages=messages,
                                               output_format=schema, **kwargs)
        _check_stop(response, model)
        if response.parsed_output is None:
            raise LLMError(f"{model} returned no parseable answer.")
        return response.parsed_output

    # No structured-output feature every provider shares: schema in the prompt, validate, repair once.
    instructions = (f"{system}\n\n" if system else "") + (
        "Respond with a single JSON object and nothing else. It must match this JSON Schema:\n"
        + json.dumps(schema.model_json_schema()))
    convo = [{"role": "system", "content": instructions}, *messages]
    options = {"max_tokens": max_tokens, "response_format": {"type": "json_object"}}
    for attempt in range(2):
        reply = _openai_call(model, convo, options)
        try:
            return schema.model_validate_json(_json_text(reply))
        except ValidationError as e:
            if attempt == 1:
                raise LLMError(f"{model} twice returned JSON that didn't fit the schema. Use a stronger model for this role.")
            first = e.errors()[0]
            convo = [*convo, {"role": "assistant", "content": reply},
                     {"role": "user", "content": f"That JSON didn't match the schema ({first['msg']} at {first['loc']}). "
                                                 "Reply with only the corrected JSON object."}]
    raise AssertionError("unreachable")
