"""Embedding service — Gemini primary, OpenAI fallback.

This module is the single entry point for every vector the recommender
produces. Callers never talk to provider SDKs directly.

Design goals
------------
1.  **Model-tagged output.** Every vector is returned alongside the model
    name that produced it so callers can store it unchanged in
    ``job_embeddings.model`` / ``user_embeddings.model``. The read path
    filters on that column to keep job/user dims consistent even across a
    provider switch.
2.  **Free-tier first.** Gemini ``text-embedding-004`` (768 dims) is the
    default; OpenAI ``text-embedding-3-small`` (1536 dims) is only used if
    Gemini fails AND ``AI_PROVIDER_FALLBACK_ENABLED`` is ``True``.
3.  **Bounded failure.** Every provider call has a hard timeout and is
    retried at most once. There is no infinite retry loop.
4.  **Deterministic batching.** Input order is preserved. Duplicate inputs
    within a batch are collapsed to a single API call and re-expanded on
    the way out.

See ``docs/RECOMMENDATIONS_V2_PLAN.md`` §3.1 for the policy, §5.6 for the
pipeline, and §10 for the vendor-switch failure modes this guards against.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# --- Provider shims -------------------------------------------------------
# We import lazily so a missing dependency on one provider doesn't prevent
# the other from working. The shims only do the single thing we need them
# to do (embed a list of strings), which keeps them tiny and testable.

try:
    import google.generativeai as _genai  # type: ignore
    _GEMINI_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dep
    _genai = None  # type: ignore
    _GEMINI_SDK_AVAILABLE = False

try:
    from openai import AsyncOpenAI as _AsyncOpenAI  # type: ignore
    _OPENAI_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dep
    _AsyncOpenAI = None  # type: ignore
    _OPENAI_SDK_AVAILABLE = False


# --- Public types ---------------------------------------------------------


@dataclass(frozen=True)
class EmbeddingResult:
    """Single embedding result tagged with the producing model.

    ``vector`` is a plain ``list[float]`` so it can be written directly into
    pgvector or a ``float8[]`` column without any further conversion, and
    so it's JSON-serializable for Celery task payloads.
    """

    vector: List[float]
    model: str
    dims: int
    provider: str


# Distinct exception so callers can distinguish "both providers died" from
# a bug in the calling code.
class EmbeddingUnavailableError(RuntimeError):
    """Raised when no provider can produce an embedding.

    The pipeline treats this as "skip this job/user for now, try again on
    the next run". It is NEVER silently swallowed into a zero-vector —
    that would poison downstream cosine math.
    """


# --- Module-level clients (lazy singletons) ------------------------------

_openai_client: Optional["_AsyncOpenAI"] = None  # type: ignore[name-defined]
_gemini_configured: bool = False


def _gemini_ready() -> bool:
    """Prepare the google.generativeai SDK. Idempotent."""
    global _gemini_configured
    if not _GEMINI_SDK_AVAILABLE or not settings.GEMINI_API_KEY:
        return False
    if not _gemini_configured:
        _genai.configure(api_key=settings.GEMINI_API_KEY)  # type: ignore[union-attr]
        _gemini_configured = True
    return True


def _openai() -> Optional["_AsyncOpenAI"]:  # type: ignore[name-defined]
    """Return a cached AsyncOpenAI client, or None if not configured."""
    global _openai_client
    if not _OPENAI_SDK_AVAILABLE or not settings.OPENAI_API_KEY:
        return None
    if _openai_client is None:
        _openai_client = _AsyncOpenAI(api_key=settings.OPENAI_API_KEY)  # type: ignore[misc]
    return _openai_client


# --- Helpers --------------------------------------------------------------


def source_hash(text: str) -> str:
    """Stable hash of input text, used to short-circuit re-embedding.

    SHA-256 is overkill, but it's fast enough, collision-free in practice,
    and matches what we store in ``job_embeddings.source_hash``.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _dedupe(texts: Sequence[str]) -> tuple[List[str], List[int]]:
    """Collapse duplicate inputs while preserving order.

    Returns ``(unique_texts, inverse_index)`` where
    ``inverse_index[i]`` is the position in ``unique_texts`` that
    corresponds to ``texts[i]``. This lets us expand a provider batch back
    into the caller's original order even when inputs repeat.
    """
    seen: Dict[str, int] = {}
    unique: List[str] = []
    inverse: List[int] = []
    for t in texts:
        if t in seen:
            inverse.append(seen[t])
        else:
            seen[t] = len(unique)
            inverse.append(seen[t])
            unique.append(t)
    return unique, inverse


# --- Provider calls -------------------------------------------------------


async def _embed_with_gemini(texts: Sequence[str], model: str) -> List[List[float]]:
    """Embed a batch via Gemini. Returns one vector per input in the same order."""
    if not _gemini_ready():
        raise EmbeddingUnavailableError("Gemini SDK missing or GEMINI_API_KEY empty.")

    # The sync Gemini call is cheap (HTTP) but we still run it in a thread
    # so the event loop stays responsive. Older versions of
    # google-generativeai don't expose an async embed_content; this keeps
    # us compatible with all of them.
    def _sync_call() -> List[List[float]]:
        # The SDK accepts a list of strings directly and returns one
        # embedding per input under ``embedding``. See
        # https://ai.google.dev/api/embeddings.
        resp = _genai.embed_content(  # type: ignore[union-attr]
            model=f"models/{model}" if not model.startswith("models/") else model,
            content=list(texts),
            task_type="retrieval_document",
        )
        raw = resp.get("embedding") if isinstance(resp, dict) else getattr(resp, "embedding", None)
        if raw is None:
            raise EmbeddingUnavailableError("Gemini response missing 'embedding' field.")
        # Single-input calls return a flat list; batched calls return a
        # list-of-lists. Normalize both to list-of-lists.
        if raw and isinstance(raw[0], (float, int)):
            return [[float(x) for x in raw]]
        return [[float(x) for x in row] for row in raw]

    return await asyncio.to_thread(_sync_call)


async def _embed_with_openai(texts: Sequence[str], model: str) -> List[List[float]]:
    """Embed a batch via OpenAI. Returns one vector per input in the same order."""
    client = _openai()
    if client is None:
        raise EmbeddingUnavailableError("OpenAI SDK missing or OPENAI_API_KEY empty.")
    resp = await client.embeddings.create(model=model, input=list(texts))
    # OpenAI returns results in the same order as the input batch.
    return [list(item.embedding) for item in resp.data]


# --- Public API -----------------------------------------------------------


async def embed_texts(
    texts: Sequence[str],
    *,
    task: str = "document",
) -> List[EmbeddingResult]:
    """Embed a list of texts using the configured provider, with fallback.

    Args:
        texts: Input strings. Must be non-empty and ≤ ~8KB each for the
            Gemini free tier. Caller is responsible for trimming.
        task: Logical hint (``"document"`` or ``"query"``). Currently
            informational; used for telemetry only. Embeddings are already
            produced by a task-specific model so we don't pass this to the
            provider.

    Returns:
        A list of :class:`EmbeddingResult`, one per input, in the same
        order. All results in the list are produced by the SAME provider
        (partial fallback is not supported — either the whole batch
        succeeds on one side, or the whole batch is retried on the other).

    Raises:
        EmbeddingUnavailableError: if neither provider can serve the batch.
    """
    if not texts:
        return []
    if any(t is None for t in texts):
        raise ValueError("embed_texts() does not accept None inputs.")

    unique, inverse = _dedupe(texts)

    primary = (settings.AI_EMBEDDING_PROVIDER or "gemini").lower()
    primary_model = settings.AI_EMBEDDING_MODEL or "text-embedding-004"
    fallback_enabled = bool(settings.AI_PROVIDER_FALLBACK_ENABLED)
    timeout = max(1.0, float(settings.AI_EMBEDDING_TIMEOUT_SECONDS))

    order = [
        (primary, primary_model),
        *(
            [("openai", "text-embedding-3-small") if primary != "openai" else ("gemini", "text-embedding-004")]
            if fallback_enabled
            else []
        ),
    ]

    last_error: Optional[Exception] = None
    for attempt, (provider, model) in enumerate(order):
        started = time.monotonic()
        try:
            if provider == "gemini":
                vectors = await asyncio.wait_for(
                    _embed_with_gemini(unique, model), timeout=timeout
                )
            elif provider == "openai":
                vectors = await asyncio.wait_for(
                    _embed_with_openai(unique, model), timeout=timeout
                )
            else:
                raise EmbeddingUnavailableError(f"Unknown embedding provider: {provider!r}")
        except (asyncio.TimeoutError, Exception) as exc:  # noqa: BLE001 — we re-raise below
            last_error = exc
            elapsed = time.monotonic() - started
            logger.warning(
                "Embedding attempt failed",
                extra={
                    "provider": provider,
                    "model": model,
                    "attempt": attempt,
                    "task": task,
                    "batch_size": len(unique),
                    "error": repr(exc),
                    "elapsed_ms": round(elapsed * 1000, 1),
                },
            )
            continue

        if len(vectors) != len(unique):
            # Defensive: if the provider ever desyncs input/output length,
            # don't silently mis-assign vectors to jobs.
            last_error = EmbeddingUnavailableError(
                f"{provider}: expected {len(unique)} vectors, got {len(vectors)}"
            )
            logger.error(str(last_error))
            continue

        dims = len(vectors[0]) if vectors else 0
        elapsed = time.monotonic() - started
        logger.info(
            "Embedding succeeded",
            extra={
                "provider": provider,
                "model": model,
                "task": task,
                "batch_size": len(unique),
                "dims": dims,
                "elapsed_ms": round(elapsed * 1000, 1),
                "attempt": attempt,  # 0 = primary, 1 = fallback
            },
        )
        # Expand back to the caller's original order.
        results = [
            EmbeddingResult(
                vector=vectors[inv_idx],
                model=model,
                dims=dims,
                provider=provider,
            )
            for inv_idx in inverse
        ]
        return results

    raise EmbeddingUnavailableError(
        f"All embedding providers failed. Last error: {last_error!r}"
    )


async def embed_one(text: str, *, task: str = "document") -> EmbeddingResult:
    """Embed a single text. Thin wrapper around :func:`embed_texts`."""
    [result] = await embed_texts([text], task=task)
    return result
