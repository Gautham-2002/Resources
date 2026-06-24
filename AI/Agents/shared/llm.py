"""
Shared OpenAI client wrapper for all modules.
Provides both sync and async interfaces.
"""

from openai import OpenAI, AsyncOpenAI
from .config import get_openai_api_key, get_model_name


def get_openai_client() -> OpenAI:
    """Get a synchronous OpenAI client."""
    return OpenAI(api_key=get_openai_api_key())


def get_async_openai_client() -> AsyncOpenAI:
    """Get an asynchronous OpenAI client."""
    return AsyncOpenAI(api_key=get_openai_api_key())


def chat(
    prompt: str,
    system: str = "You are a helpful assistant.",
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str:
    """Simple synchronous chat completion."""
    client = get_openai_client()
    response = client.chat.completions.create(
        model=model or get_model_name(),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


async def achat(
    prompt: str,
    system: str = "You are a helpful assistant.",
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str:
    """Simple asynchronous chat completion."""
    client = get_async_openai_client()
    response = await client.chat.completions.create(
        model=model or get_model_name(),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""
