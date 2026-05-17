"""Azure OpenAI async client wrapper with deployment rotation and failover."""

import asyncio
import itertools
import logging
from openai import AsyncAzureOpenAI, APIStatusError, APITimeoutError, APIConnectionError

from app.config import get_settings

_client: AsyncAzureOpenAI | None = None
_deployment_cycle = None
_logger = logging.getLogger(__name__)

# Transient HTTP status codes that warrant retry on another deployment
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


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


async def _call_with_failover(messages, temperature, max_tokens, response_format=None):
    """Call completions with failover across deployments on transient errors."""
    settings = get_settings()
    num_deployments = len(settings.azure_openai_deployments)
    client = _get_client()
    last_error = None

    for _ in range(num_deployments):
        deployment = _next_deployment()
        kwargs = dict(model=deployment, messages=messages, temperature=temperature, max_tokens=max_tokens)
        if response_format:
            kwargs["response_format"] = response_format
        try:
            return await client.chat.completions.create(**kwargs)
        except APIStatusError as e:
            if e.status_code in _RETRYABLE_STATUS:
                _logger.warning("Deployment %s returned %s, trying next", deployment, e.status_code)
                last_error = e
                continue
            raise
        except (APITimeoutError, APIConnectionError) as e:
            _logger.warning("Deployment %s timed out / connection error, trying next", deployment)
            last_error = e
            continue

    raise last_error  # All deployments exhausted


async def generate_sql(system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
    """Generate SQL from a system+user prompt pair. Returns raw SQL string."""
    response = await _call_with_failover(
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=temperature, max_tokens=2000,
    )
    content = response.choices[0].message.content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines).strip()
    return content


async def generate_narrative(system_prompt: str, evidence_text: str, temperature: float = 0.3) -> str:
    """Generate a human-readable narrative from evidence."""
    response = await _call_with_failover(
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": evidence_text}],
        temperature=temperature, max_tokens=1500,
    )
    return response.choices[0].message.content.strip()


async def generate_json(system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
    """Generate a JSON response from a system+user prompt pair."""
    response = await _call_with_failover(
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=temperature, max_tokens=2000,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content.strip()
