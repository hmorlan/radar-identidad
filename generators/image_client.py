"""
Unified Image Client Abstraction

Provides mode-based image generation:
- native: Uses google-genai SDK directly for Google Gemini API
- openai-compatible: Uses REST chat/completions format for LiteLLM proxies
- openrouter: Uses OpenRouter's dedicated /api/v1/images endpoint (supports
  aspect_ratio, resolution tiers, and input_references for image-to-image)

Follows the same factory pattern as agents/llm_client.py for consistency.
"""

import asyncio
import io
import base64
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import httpx
from PIL import Image

from google import genai
from google.genai import types, errors

if TYPE_CHECKING:
    from agents.config import ImageProviderConfig

logger = logging.getLogger(__name__)

# Retry policy for transient image-generation failures (connection drops,
# timeouts, 429s, and 5xx). A single dropped connection used to lose the entire
# daily hero image with no retry (e.g. "Server disconnected without sending a
# response" on 2026-06-26). A short 3-attempt/~25s window then proved too
# shallow: on 2026-06-27 the RDSec proxy fast-failed (~3s each) on all 3 tries
# inside ~25s, dropping the hero, yet a manual regen later succeeded first try --
# the provider blip simply outlasted the tiny retry window. So we widen the
# window to span several minutes: more attempts with capped exponential backoff,
# so a multi-minute transient outage self-heals. The per-request timeout (180s)
# is unchanged -- it was never the issue (today's failures were instant
# disconnects, not timeouts).
#
# Backoff schedule (base 3.0, cap 60): ~3, 6, 12, 24, 48, 60 s between the 7
# attempts => ~153s of pure backoff + jitter + request time, i.e. the retry
# window now spans roughly 3 minutes instead of 25 seconds.
DEFAULT_MAX_ATTEMPTS = 7
DEFAULT_RETRY_BASE_DELAY = 3.0  # seconds; exponential: ~3s, 6s, 12s, 24s ...
DEFAULT_RETRY_MAX_DELAY = 60.0  # seconds; cap per-retry backoff so it stays bounded


def _is_retryable_status(status_code: int) -> bool:
    """True for transient HTTP statuses worth retrying (429 + any 5xx)."""
    return status_code == 429 or status_code >= 500


def _backoff_delay(attempt: int, base_delay: float, max_delay: float) -> float:
    """Exponential backoff with jitter for retry attempt N (1-indexed), capped."""
    base = base_delay * (2 ** (attempt - 1))
    base = min(base, max_delay)
    return base + random.uniform(0, base_delay / 2)


async def _post_json_with_retries(
    url: str,
    headers: Dict[str, str],
    body: Dict[str, Any],
    timeout: float,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    retry_base_delay: float = DEFAULT_RETRY_BASE_DELAY,
    retry_max_delay: float = DEFAULT_RETRY_MAX_DELAY,
    troubleshooting: str = "",
) -> Dict[str, Any]:
    """POST a JSON body and return the parsed response, retrying transient failures.

    Shared by every REST image client so they inherit one retry policy: retries
    on connection drops, timeouts, 429s, and 5xx with capped exponential backoff
    (see the window rationale above); non-transient 4xx fails fast on the first
    attempt. ``troubleshooting`` is appended to the raised RuntimeError so each
    caller can give mode-specific guidance.
    """
    data = None
    for attempt in range(1, max_attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=body
                )
                response.raise_for_status()
                data = response.json()
            break  # success

        except httpx.TimeoutException as e:
            if attempt < max_attempts:
                delay = _backoff_delay(attempt, retry_base_delay, retry_max_delay)
                logger.warning(
                    f"Image generation timed out after {timeout}s "
                    f"(attempt {attempt}/{max_attempts}); retrying in {delay:.1f}s"
                )
                await asyncio.sleep(delay)
                continue
            error_msg = f"Image generation timed out after {timeout}s ({max_attempts} attempts)"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if _is_retryable_status(status) and attempt < max_attempts:
                delay = _backoff_delay(attempt, retry_base_delay, retry_max_delay)
                logger.warning(
                    f"Image generation API returned status {status} "
                    f"(attempt {attempt}/{max_attempts}); retrying in {delay:.1f}s"
                )
                await asyncio.sleep(delay)
                continue
            error_msg = (
                f"Image generation API error (status={status}): "
                f"{e.response.text[:500]}"
            )
            if troubleshooting:
                error_msg += f"\n\n{troubleshooting}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except httpx.RequestError as e:
            # Connection drops / DNS / read errors (e.g. "Server disconnected
            # without sending a response") -- treat as transient.
            if attempt < max_attempts:
                delay = _backoff_delay(attempt, retry_base_delay, retry_max_delay)
                logger.warning(
                    f"Image generation request failed: {e} "
                    f"(attempt {attempt}/{max_attempts}); retrying in {delay:.1f}s"
                )
                await asyncio.sleep(delay)
                continue
            error_msg = f"Image generation request failed: {e}"
            if troubleshooting:
                error_msg += f"\n\n{troubleshooting}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    return data


def _sniff_mime(data: bytes) -> str:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


@dataclass
class ImageResponse:
    """Response from image generation."""
    image_data: bytes  # Raw image bytes
    mime_type: str = "image/png"
    # Token accounting, when the provider reports it.
    #
    # The openai-compatible path goes through /v1/chat/completions, whose schema
    # includes a `usage` block -- but whether a given proxy populates it for an
    # *image* response is a property of that deployment, not of the schema. The
    # native path exposes `usage_metadata` on the SDK response, likewise optional.
    #
    # None means "the provider told us nothing", which is different from zero. The
    # replay renders `n/a` for None and a real figure otherwise; it must never show
    # $0.000 for a call that was in fact billed.
    usage: Optional[Dict[str, Any]] = None
    model: Optional[str] = None


class BaseImageClient(ABC):
    """Abstract base class for image generation clients."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        reference_image: Optional[bytes] = None,
        aspect_ratio: str = "21:9",
        image_size: str = "2K"
    ) -> ImageResponse:
        """
        Generate an image from a prompt.

        Args:
            prompt: Text prompt describing the image to generate
            reference_image: Optional reference image bytes for style/content guidance
            aspect_ratio: Image aspect ratio (default "21:9" for hero banners)
            image_size: Image resolution (default "2K")

        Returns:
            ImageResponse with raw image bytes and mime type
        """
        pass


def native_usage_to_openai_shape(meta: Any) -> Optional[Dict[str, Any]]:
    """Normalise google-genai ``usage_metadata`` to the openai-compatible shape.

    Gemini reports thinking separately (``thoughts_token_count``) from the
    candidate output, and breaks the candidates down by modality. Thinking is
    billed (at the text rate), so it must be part of ``completion_tokens``, and
    the modality split lets ``price_image_usage`` charge image and text tokens
    at their own rates.
    """
    if meta is None:
        return None

    def _n(value: Any) -> int:
        return int(value) if isinstance(value, (int, float)) else 0

    candidates = _n(getattr(meta, "candidates_token_count", None))
    thoughts = _n(getattr(meta, "thoughts_token_count", None))
    image_tokens = text_tokens = 0
    for detail in getattr(meta, "candidates_tokens_details", None) or []:
        modality = str(getattr(detail, "modality", "")).upper()
        count = _n(getattr(detail, "token_count", None))
        if "IMAGE" in modality:
            image_tokens += count
        elif "TEXT" in modality:
            text_tokens += count
    if not image_tokens and not text_tokens:
        image_tokens = candidates

    usage: Dict[str, Any] = {}
    prompt = getattr(meta, "prompt_token_count", None)
    if prompt is not None:
        usage["prompt_tokens"] = _n(prompt)
    if candidates or thoughts:
        usage["completion_tokens"] = candidates + thoughts
        usage["completion_tokens_details"] = {
            "image_tokens": image_tokens,
            "text_tokens": text_tokens,
            "reasoning_tokens": thoughts,
        }
    total = getattr(meta, "total_token_count", None)
    if total is not None:
        usage["total_tokens"] = _n(total)
    return usage or None


class NativeGeminiClient(BaseImageClient):
    """
    Image client using google-genai SDK (native mode).

    Uses the official Google SDK for direct Gemini API access.
    Recommended for users with Google AI API keys.
    """

    # v3.2 (docs/identidad-visual.md §6). Se verifica con scripts/check_image_model.py.
    DEFAULT_MODEL = "gemini-3-pro-image"
    API_VERSION = "v1beta"

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        timeout: float = 180.0
    ):
        """
        Initialize native Gemini client.

        Args:
            api_key: Google AI API key (explicit, not from env vars)
            model: Model name (default: gemini-3-pro-image)
            timeout: Request timeout in seconds (converted to ms for SDK)
        """
        self.model = model or self.DEFAULT_MODEL
        self.timeout = timeout

        # Create client with explicit API key and retry options
        # SDK uses milliseconds for timeout
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=int(timeout * 1000),
                # Los modelos preview (gemini-3-pro-image-preview) solo existen en
                # v1beta; versiones recientes del SDK pueden usar v1 por defecto.
                api_version=self.API_VERSION,
            )
        )

        logger.info(f"NativeGeminiClient initialized with model={self.model}, timeout={timeout}s")

    async def generate(
        self,
        prompt: str,
        reference_image: Optional[bytes] = None,
        aspect_ratio: str = "21:9",
        image_size: str = "2K",
        reference_images: Optional[List[bytes]] = None,
    ) -> ImageResponse:
        """Generate image using google-genai SDK.

        ``reference_images`` (v3.2) sends several style references before the
        prompt; ``reference_image`` is kept for older callers.
        """
        contents = []

        # Add reference images if provided (must be PIL Image for SDK)
        for ref in ([reference_image] if reference_image else []) + list(reference_images or []):
            contents.append(Image.open(io.BytesIO(ref)))

        contents.append(prompt)

        try:
            # Use async client (client.aio)
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size=image_size
                    )
                )
            )
        except errors.APIError as e:
            error_msg = (
                f"Gemini API error (code={e.code}): {e.message}\n\n"
                f"Troubleshooting (native mode):\n"
                f"- Verify your Google API key has access to {self.model}\n"
                f"- Check quotas at https://console.cloud.google.com/apis/dashboard\n"
                f"- Ensure the model name is correct for your API access level"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

        # The SDK exposes counts as `usage_metadata`; normalise to the same key
        # names the openai-compatible path yields so downstream code sees one shape.
        usage = native_usage_to_openai_shape(getattr(response, "usage_metadata", None))
        logger.info(
            f"Image usage reported: {usage}"
            if usage
            else "Image response carried no usage metadata; cost will show as n/a"
        )

        # Extract image from response parts
        for part in response.parts:
            if part.inline_data:
                return ImageResponse(
                    image_data=part.inline_data.data,
                    mime_type=part.inline_data.mime_type or "image/png",
                    usage=usage,
                    model=self.model,
                )

        raise RuntimeError(
            "No image returned from Gemini API. "
            "Check that the model supports image generation and the prompt is valid."
        )

    async def generate_batch(
        self,
        prompts: List[str],
        reference_images: Optional[List[bytes]] = None,
        aspect_ratio: str = "21:9",
        image_size: str = "2K",
        max_wait_seconds: float = 1800.0,
        poll_seconds: float = 20.0,
    ) -> List[Optional[ImageResponse]]:
        """Generate several images through the Gemini Batch API (half price).

        Returns one entry per prompt (None for a request that produced no image).
        Raises TimeoutError if the job does not finish within ``max_wait_seconds``
        -- the job is cancelled first, so nothing is billed twice when the caller
        falls back to the synchronous path -- and RuntimeError on API errors.
        Each response's ``usage`` carries ``"batch": True``.
        """
        import asyncio
        import time

        ref_parts = [
            types.Part.from_bytes(data=ref, mime_type=_sniff_mime(ref))
            for ref in (reference_images or [])
        ]
        requests = [
            types.InlinedRequest(
                contents=[types.Content(role="user", parts=ref_parts + [types.Part.from_text(text=p)])],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio=aspect_ratio, image_size=image_size),
                ),
            )
            for p in prompts
        ]
        try:
            job = await self.client.aio.batches.create(
                model=self.model,
                src=requests,
                config=types.CreateBatchJobConfig(display_name="radar-hero"),
            )
        except errors.APIError as e:
            raise RuntimeError(f"Gemini batch create failed (code={e.code}): {e.message}") from e

        done = {"JOB_STATE_SUCCEEDED", "JOB_STATE_PARTIALLY_SUCCEEDED", "JOB_STATE_FAILED",
                "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"}
        started = time.monotonic()
        logger.info(f"Gemini batch {job.name} created with {len(prompts)} request(s)")
        while True:
            state = str(getattr(job.state, "name", job.state))
            if state in done:
                break
            if time.monotonic() - started > max_wait_seconds:
                try:
                    await self.client.aio.batches.cancel(name=job.name)
                    logger.warning(f"Gemini batch {job.name} cancelled after {max_wait_seconds:.0f}s")
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"Could not cancel Gemini batch {job.name}: {e}")
                raise TimeoutError(f"Gemini batch {job.name} still {state} after {max_wait_seconds:.0f}s")
            await asyncio.sleep(poll_seconds)
            job = await self.client.aio.batches.get(name=job.name)

        if state not in ("JOB_STATE_SUCCEEDED", "JOB_STATE_PARTIALLY_SUCCEEDED"):
            raise RuntimeError(f"Gemini batch {job.name} ended in {state}: {getattr(job, 'error', None)}")

        out: List[Optional[ImageResponse]] = []
        inlined = (job.dest.inlined_responses if job.dest else None) or []
        for item in inlined:
            response = getattr(item, "response", None)
            image = None
            if response is not None:
                usage = native_usage_to_openai_shape(getattr(response, "usage_metadata", None))
                if usage is not None:
                    usage["batch"] = True
                for part in (response.parts or []):
                    if part.inline_data:
                        image = ImageResponse(
                            image_data=part.inline_data.data,
                            mime_type=part.inline_data.mime_type or "image/png",
                            usage=usage,
                            model=self.model,
                        )
                        break
            if image is None:
                logger.warning(f"Batch request returned no image: {getattr(item, 'error', None)}")
            out.append(image)
        while len(out) < len(prompts):
            out.append(None)
        return out


class OpenAICompatibleClient(BaseImageClient):
    """
    Image client using OpenAI chat/completions format (openai-compatible mode).

    Uses REST API for LiteLLM or other OpenAI-compatible proxies.
    Refactored from existing HeroGenerator implementation.
    """

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        model: str,
        timeout: float = 180.0,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        retry_base_delay: float = DEFAULT_RETRY_BASE_DELAY,
        retry_max_delay: float = DEFAULT_RETRY_MAX_DELAY
    ):
        """
        Initialize OpenAI-compatible client.

        Args:
            api_key: API key for Bearer authentication
            endpoint: API endpoint URL (auto-appends /chat/completions if ends with /v1)
            model: Model name for the proxy
            timeout: Request timeout in seconds
            max_attempts: Total attempts (incl. first) on transient failures
            retry_base_delay: Base seconds for exponential backoff between retries
            retry_max_delay: Cap (seconds) on any single backoff sleep so a long
                retry window stays bounded per-step
        """
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_attempts = max(1, max_attempts)
        self.retry_base_delay = max(0.0, retry_base_delay)
        self.retry_max_delay = max(0.0, retry_max_delay)

        # Auto-append /chat/completions if endpoint ends with /v1
        if endpoint.rstrip('/').endswith('/v1'):
            self.endpoint = endpoint.rstrip('/') + '/chat/completions'
        else:
            self.endpoint = endpoint

        logger.info(f"OpenAICompatibleClient initialized with endpoint={self.endpoint}, model={self.model}")

    def _backoff_delay(self, attempt: int) -> float:
        """Exponential backoff with jitter for retry attempt N (1-indexed), capped."""
        return _backoff_delay(attempt, self.retry_base_delay, self.retry_max_delay)

    @staticmethod
    def _troubleshooting(endpoint: str, model: str) -> str:
        return (
            f"Troubleshooting (openai-compatible mode):\n"
            f"- Verify your proxy endpoint supports image generation\n"
            f"- Check that the model name '{model}' is correct for your proxy\n"
            f"- Verify the endpoint URL is correct: {endpoint}\n"
            f"- Ensure the API key has proper permissions"
        )

    async def generate(
        self,
        prompt: str,
        reference_image: Optional[bytes] = None,
        aspect_ratio: str = "21:9",
        image_size: str = "2K"
    ) -> ImageResponse:
        """Generate image using OpenAI chat/completions format."""
        # Build message content
        content = []
        if reference_image:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64.b64encode(reference_image).decode()}"
                }
            })
        content.append({"type": "text", "text": prompt})

        request_body = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 1.0,  # Required by Gemini image models
            "modalities": ["image", "text"],
            "image_config": {
                "aspect_ratio": aspect_ratio,
                "image_size": image_size
            }
        }

        # Transient failures (connection drops, timeouts, 429, 5xx) retry with
        # capped exponential backoff via the shared helper; 4xx fails fast.
        data = await _post_json_with_retries(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            body=request_body,
            timeout=self.timeout,
            max_attempts=self.max_attempts,
            retry_base_delay=self.retry_base_delay,
            retry_max_delay=self.retry_max_delay,
            troubleshooting=self._troubleshooting(self.endpoint, self.model),
        )

        # Extract image from response
        message = data.get("choices", [{}])[0].get("message", {})
        images = message.get("images", [])

        if not images:
            error_content = message.get("content", "Unknown error - no images returned")
            raise RuntimeError(f"No image returned from API: {error_content}")

        image_url = images[0].get("image_url", {}).get("url", "")
        if not image_url or "," not in image_url:
            raise RuntimeError("Invalid image URL format in response - expected base64 data URL")

        # Parse base64 data URL (format: data:image/png;base64,<data>)
        image_base64 = image_url.split(",", 1)[1]

        # `usage` is optional in practice: the schema defines it, but whether this
        # proxy fills it in for an image response is a deployment detail. Log what
        # we got (keys only -- the values are counts, but the log is not the place
        # to grow) so a missing block is diagnosable rather than silent.
        usage = data.get("usage")
        if usage:
            logger.info(f"Image usage reported: {usage}")
        else:
            logger.info("Image response carried no usage block; cost will show as n/a")

        return ImageResponse(
            image_data=base64.b64decode(image_base64),
            mime_type="image/png",
            usage=usage if isinstance(usage, dict) else None,
            model=data.get("model") or self.model,
        )


class OpenRouterImageClient(BaseImageClient):
    """
    Image client using OpenRouter's dedicated /api/v1/images endpoint.

    Chosen over OpenRouter's chat/completions image path because /images
    natively supports what the daily hero needs:
    - aspect_ratio ("21:9" hero banners; chat/completions would ignore it)
    - resolution tiers ("2K")
    - input_references for image-to-image (optional style reference image)

    Response shape per OpenRouter docs: data[0].b64_json + media_type, plus a
    usage block with prompt/completion token counts.
    """

    DEFAULT_ENDPOINT = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL = "google/gemini-3-pro-image"

    def __init__(
        self,
        api_key: str,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        quality: Optional[str] = None,
        timeout: float = 180.0,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        retry_base_delay: float = DEFAULT_RETRY_BASE_DELAY,
        retry_max_delay: float = DEFAULT_RETRY_MAX_DELAY
    ):
        """
        Initialize OpenRouter image client.

        Args:
            api_key: OpenRouter API key for Bearer authentication
            endpoint: API base URL ending at the version segment
                (default https://openrouter.ai/api/v1); /images is appended
            model: OpenRouter model slug (default google/gemini-3-pro-image)
            quality: Optional rendering quality (auto/low/medium/high)
            timeout: Request timeout in seconds
            max_attempts/retry_*: Shared transient-failure retry policy
        """
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL
        self.quality = quality or None
        self.timeout = timeout
        self.max_attempts = max(1, max_attempts)
        self.retry_base_delay = max(0.0, retry_base_delay)
        self.retry_max_delay = max(0.0, retry_max_delay)
        # Normalize once so generate() can just append the resource path.
        self.endpoint = (endpoint or self.DEFAULT_ENDPOINT).rstrip('/')

        logger.info(
            f"OpenRouterImageClient initialized with endpoint={self.endpoint}/images, "
            f"model={self.model}, quality={self.quality or 'default'}"
        )

    async def generate(
        self,
        prompt: str,
        reference_image: Optional[bytes] = None,
        aspect_ratio: str = "21:9",
        image_size: str = "2K"
    ) -> ImageResponse:
        """Generate image via POST {endpoint}/images."""
        body: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "resolution": image_size,
        }
        if self.quality:
            body["quality"] = self.quality
        if reference_image:
            body["input_references"] = [{
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64.b64encode(reference_image).decode()}"
                }
            }]

        data = await _post_json_with_retries(
            f"{self.endpoint}/images",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            body=body,
            timeout=self.timeout,
            max_attempts=self.max_attempts,
            retry_base_delay=self.retry_base_delay,
            retry_max_delay=self.retry_max_delay,
            troubleshooting=(
                f"Troubleshooting (openrouter mode):\n"
                f"- Check that '{self.model}' supports image output on OpenRouter\n"
                f"- Verify the API key has credit available\n"
                f"- Verify the endpoint URL is correct: {self.endpoint}/images"
            ),
        )

        images = data.get("data") if isinstance(data, dict) else None
        if not images:
            error_content = data.get("error", "Unknown error - no images returned") if isinstance(data, dict) else str(data)[:500]
            raise RuntimeError(f"No image returned from OpenRouter API: {error_content}")

        first = images[0]
        b64 = first.get("b64_json", "")
        if not b64:
            raise RuntimeError("No b64_json in OpenRouter image response")

        usage = data.get("usage")
        if usage:
            logger.info(f"Image usage reported: {usage}")
        else:
            logger.info("Image response carried no usage block; cost will show as n/a")

        return ImageResponse(
            image_data=base64.b64decode(b64),
            mime_type=first.get("media_type") or "image/png",
            usage=usage if isinstance(usage, dict) else None,
            model=data.get("model") or self.model,
        )


class ImageClient:
    """
    Factory class for creating image clients based on configuration.

    Usage:
        client = ImageClient.from_config(config)
        response = await client.generate(prompt, reference_image)
    """

    @classmethod
    def from_config(cls, config: 'ImageProviderConfig') -> BaseImageClient:
        """
        Create appropriate image client based on config mode.

        Args:
            config: ImageProviderConfig with mode, api_key, endpoint, model

        Returns:
            NativeGeminiClient for native mode
            OpenAICompatibleClient for openai-compatible mode
            OpenRouterImageClient for openrouter mode

        Raises:
            ValueError: If mode is unknown
        """
        if config.mode == "native":
            return NativeGeminiClient(
                api_key=config.api_key,
                model=config.model
            )
        elif config.mode == "openai-compatible":
            return OpenAICompatibleClient(
                api_key=config.api_key,
                endpoint=config.endpoint,  # Already validated by schema
                model=config.model
            )
        elif config.mode == "openrouter":
            return OpenRouterImageClient(
                api_key=config.api_key,
                endpoint=config.endpoint,  # Optional; defaults to openrouter.ai/api/v1
                model=config.model,
                quality=getattr(config, 'quality', None)
            )
        else:
            raise ValueError(
                f"Unknown image mode: {config.mode}. "
                f"Expected 'native', 'openai-compatible', or 'openrouter'."
            )
