"""
Async LLM call abstraction.

Same shape as Project 1's llm.py, but uses AsyncOpenAI so we can fire
multiple calls concurrently with asyncio.gather. Without async, three
"parallel" calls would actually run sequentially because each one would
block the event loop.
"""
import os
from typing import Type, TypeVar
from pydantic import BaseModel
from openai import AsyncOpenAI

T = TypeVar("T", bound=BaseModel)

MODEL = os.getenv("LLM_MODEL", "gpt-5.4-mini")

# Lazy-init the client so importing this module doesn't require the key
# to be set yet (useful for tests, IDE tooling, and one-off introspection).
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI()
    return _client


async def call_llm(
    prompt: str,
    schema: Type[T],
    system: str,
    temperature: float = 0.2,
) -> T:
    """
    Async LLM call with structured outputs.

    Schema-conformant Pydantic object guaranteed by the API. Same contract
    as Project 1, just `await`-able.
    """
    response = await _get_client().chat.completions.parse(
        model=MODEL,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        response_format=schema,
    )
    parsed = response.choices[0].message.parsed
    if parsed is None:
        refusal = response.choices[0].message.refusal
        raise RuntimeError(f"Model refused to respond: {refusal}")
    return parsed
