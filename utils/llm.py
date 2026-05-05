import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 32000
LOG_PATH = Path("llm_calls.jsonl")

_client = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        load_dotenv()
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to a .env file or export it in your shell."
            )
        _client = Anthropic(api_key=api_key)
    return _client


def call_llm(
    stage: str,
    source_id: str | None,
    entry_ids: list[str],
    prompt: str,
    input_artifacts: list[str],
    output_artifact: str,
) -> str:
    client = _get_client()
    label = f"{stage}/{source_id or '-'}"
    print(f"  → LLM call: {label} ({len(entry_ids)} entry_ids, prompt={len(prompt):,} chars)", flush=True)
    t0 = time.monotonic()
    with client.messages.stream(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for _ in stream.text_stream:
            pass
        response = stream.get_final_message()
    elapsed = time.monotonic() - t0
    usage = getattr(response, "usage", None)
    in_tok = getattr(usage, "input_tokens", "?") if usage else "?"
    out_tok = getattr(usage, "output_tokens", "?") if usage else "?"
    print(f"  ← LLM done:  {label} in {elapsed:.1f}s (in={in_tok}, out={out_tok}, stop={getattr(response, 'stop_reason', '?')})", flush=True)

    text_parts = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            text_parts.append(block.text)
    text = "".join(text_parts)

    if getattr(response, "stop_reason", None) == "max_tokens":
        raise RuntimeError(
            f"LLM response truncated at max_tokens={MAX_TOKENS} for stage={stage}, "
            f"source_id={source_id}. Increase MAX_TOKENS or split the input."
        )

    record = {
        "stage": stage,
        "source_id": source_id,
        "entry_ids": list(entry_ids),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "provider": "anthropic",
        "model": MODEL,
        "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "input_artifacts": list(input_artifacts),
        "output_artifact": output_artifact,
    }

    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    return text
