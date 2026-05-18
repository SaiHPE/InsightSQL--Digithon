"""Azure OpenAI async client wrapper with deployment rotation."""

import asyncio
import itertools
from openai import AsyncAzureOpenAI

from app.config import get_settings

_client: AsyncAzureOpenAI | None = None
_deployment_cycle = None


def _get_client() -> AsyncAzureOpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_key,
            api_version=settings.azure_openai_api_version,
        )
    return _client


def _next_deployment() -> str:
    """Rotate through available deployments for rate-limit resilience."""
    global _deployment_cycle
    settings = get_settings()
    if _deployment_cycle is None:
        _deployment_cycle = itertools.cycle(settings.azure_openai_deployments)
    return next(_deployment_cycle)


async def generate_sql(system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
    """Generate SQL from a system+user prompt pair. Returns raw SQL string."""
    client = _get_client()
    deployment = _next_deployment()

    response = await client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=2000,
    )

    content = response.choices[0].message.content.strip()

    # Strip markdown code fences if present
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first and last lines (```sql and ```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines).strip()

    return content


async def generate_narrative(system_prompt: str, evidence_text: str, temperature: float = 0.3) -> str:
    """Generate a human-readable narrative from evidence."""
    client = _get_client()
    deployment = _next_deployment()

    response = await client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": evidence_text},
        ],
        temperature=temperature,
        max_tokens=1500,
    )

    return response.choices[0].message.content.strip()


async def generate_json(system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
    """Generate a JSON response from a system+user prompt pair."""
    client = _get_client()
    deployment = _next_deployment()

    response = await client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )

    return response.choices[0].message.content.strip()
