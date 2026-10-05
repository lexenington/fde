"""The agent under test. Replace this with your product.

Two ways to plug in your own agent:
  1. Set AGENT_URL. The simulator POSTs {"tenant": ..., "messages": [...]} and expects {"reply": "..."}.
  2. Rewrite reply() below.

With neither, a naive baseline runs: Claude with the tenant's brief as its system prompt.
It has no tools and no hard rules, so expect it to fail policy-trap scenarios. That's the point.
"""

import json
import os
import urllib.request
from pathlib import Path

import anthropic

MODEL = "claude-opus-5-5"
TENANTS = Path(__file__).parent / "tenants"

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def reply(tenant: str, messages: list[dict]) -> str:
    """messages: [{"role": "user"|"assistant", "content": str}, ...], ending with the customer's message."""
    url = os.environ.get("AGENT_URL")
    if url:
        req = urllib.request.Request(
            url,
            data=json.dumps({"tenant": tenant, "messages": messages}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())["reply"]

    brief = (TENANTS / tenant / "brief.md").read_text(encoding="utf-8")
    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=2000,
        system=f"You are the customer support assistant for this business. Follow its policies exactly.\n\n{brief}",
        messages=messages,
    )
    return "".join(b.text for b in response.content if b.type == "text")
