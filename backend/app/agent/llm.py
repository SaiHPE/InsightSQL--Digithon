"""Azure OpenAI async client wrapper with deployment rotation and failover."""

import asyncio
import itertools
import logging
from openai import AsyncAzureOpenAI, APIStatusError, APITimeoutError, APIConnectionError, OpenAIError

from app.config import get_settings

_client: AsyncAzureOpenAI | None = None
_client_lock = asyncio.Lock()
_deployment_cycle = None
_logger = logging.getLogger(__name__)

# Transient HTTP status codes that warrant retry on another deployment
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


async def _get_client() -> AsyncAzureOpenAI:
    global _client
    async with _client_lock:
        if _client is None:
            import os
            import httpx
            import ssl

            settings = get_settings()

            # Build SSL context that trusts both system CAs and corporate proxy CA
            ssl_cert_file = os.environ.get("SSL_CERT_FILE")
            if ssl_cert_file:
                if not os.path.isfile(ssl_cert_file):
                    _logger.error("SSL_CERT_FILE is set but does not exist: %s", ssl_cert_file)
                    raise FileNotFoundError(f"SSL_CERT_FILE is set but file does not exist: {ssl_cert_file}")
                try:
                    ssl_ctx = ssl.create_default_context()  # loads system default CAs
                    ssl_ctx.load_verify_locations(cafile=ssl_cert_file)  # add corporate CA on top
                except Exception as e:
                    _logger.error("Failed to load SSL_CERT_FILE %s: %s", ssl_cert_file, e)
                    raise
                http_client = httpx.AsyncClient(verify=ssl_ctx)
                _logger.info("Using custom CA bundle: %s", ssl_cert_file)
            else:
                http_client = httpx.AsyncClient()

            _client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_key,
                api_version=settings.azure_openai_api_version,
                http_client=http_client,
            )
    return _client


async def close_client() -> None:
    """Close the OpenAI client and its underlying httpx transport."""
    global _client
    async with _client_lock:
        if _client is not None:
            await _client.close()
            _client = None


def _next_deployment() -> str:
    """Rotate through available deployments for rate-limit resilience."""
    global _deployment_cycle
    settings = get_settings()
    if _deployment_cycle is None:
        _deployment_cycle = itertools.cycle(settings.azure_openai_deployments)
    return next(_deployment_cycle)


async def _call_with_failover(messages, temperature, max_completion_tokens, response_format=None):
    """Call completions with failover across deployments on transient errors."""
    settings = get_settings()
    num_deployments = len(settings.azure_openai_deployments)
    if num_deployments == 0:
        _logger.warning("No Azure deployments configured; attempting Ollama fallback")
        client = None
    else:
        client = await _get_client()
    last_error = None

    for _ in range(num_deployments):
        deployment = _next_deployment()
        kwargs = dict(model=deployment, messages=messages, temperature=temperature, max_completion_tokens=max_completion_tokens)
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

    # Fallback to Ollama if all Azure deployments fail
    if not getattr(settings, "ollama_fallback_enabled", False):
        if num_deployments == 0:
            raise ValueError("No Azure deployments configured and Ollama fallback is disabled.")
        raise last_error or ValueError("All Azure deployments failed and Ollama fallback is disabled.")

    _logger.warning("All Azure deployments exhausted or failed. Falling back to Ollama model %s", settings.ollama_model)
    try:
        from openai import AsyncOpenAI
        # We use a separate client for Ollama without the Azure wrapper
        ollama_client = AsyncOpenAI(
            base_url=settings.ollama_endpoint,
            api_key="ollama" # required by the OpenAI client but ignored by Ollama
        )
        try:
            kwargs = dict(model=settings.ollama_model, messages=messages, temperature=temperature, max_completion_tokens=max_completion_tokens)
            if response_format:
                kwargs["response_format"] = response_format
            return await ollama_client.chat.completions.create(**kwargs)
        finally:
            await ollama_client.close()
    except OpenAIError as e:
        _logger.error("Ollama fallback failed as well: %s", e)
        if last_error is not None:
            raise last_error from e
        raise e


async def generate_sql(system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
    """Generate SQL from a system+user prompt pair. Returns raw SQL string."""
    response = await _call_with_failover(
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=temperature, max_completion_tokens=2000,
    )
    content = response.choices[0].message.content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        content = "\n".join(lines).strip()
    return content


async def generate_narrative(system_prompt: str, evidence_text: str, temperature: float = 0.3) -> str:
    """Generate a human-readable narrative from evidence."""
    response = await _call_with_failover(
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": evidence_text}],
        temperature=temperature, max_completion_tokens=1500,
    )
    return response.choices[0].message.content.strip()


async def generate_json(system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
    """Generate a JSON response from a system+user prompt pair."""
    response = await _call_with_failover(
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=temperature, max_completion_tokens=2000,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content.strip()
