"""LLM reranker for the top-K candidate pool.

One call per user per recommendation run. Input: 50 jobs already filtered
by semantic similarity. Output: per-job {score, reason} tuples in JSON.

Primary: Gemini 1.5 Flash (free tier). Fallback: OpenAI ``gpt-4o-mini``.
When everything fails we return ``None`` and the caller keeps the existing
``semantic_fit`` ordering — recommendations never BLOCK on the reranker.

See ``docs/RECOMMENDATIONS_V2_PLAN.md`` §5.4 for the contract and
guardrails enforced here.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass
from typing import Iterable, List, Mapping, Optional, Sequence

from app.ai.base import TaskType
from app.ai.router import get_model_router
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# Hard limits from the plan.
MAX_CANDIDATES = 50
DESCRIPTION_CHAR_BUDGET = 400
REASON_WORD_BUDGET = 20
SCORE_MIN, SCORE_MAX = 0, 100
MIN_ITEMS_FOR_VALID_RESPONSE = 30  # below this we reject and fall back


SYSTEM_PROMPT = (
    "You are scoring job fit for a candidate. You will receive the "
    "candidate's target titles, top skills, and up to 50 candidate jobs "
    "(title + short description + company). Return a STRICT JSON array of "
    '{"job_id": "...", "score": 0-100, "reason": "..."} ordered by score '
    "desc. Use 85+ only for roles that clearly match the candidate's "
    "target title AND use at least one of their top skills. Use 60-84 for "
    "adjacent roles. Use <60 for everything else. Never invent facts. "
    f"Each reason MUST be <= {REASON_WORD_BUDGET} words. Output ONLY the "
    "JSON array — no prose, no markdown, no code fences."
)


@dataclass(frozen=True)
class RerankCandidate:
    """Input candidate for the reranker. Caller trims descriptions first."""

    job_id: str
    title: str
    company: Optional[str]
    description: str  # already stripped + trimmed to DESCRIPTION_CHAR_BUDGET


@dataclass(frozen=True)
class RerankedScore:
    """Reranker verdict for one candidate."""

    job_id: str
    score: float
    reason: str


def _trim_description(text: str) -> str:
    """Safe description for the prompt: strip HTML tags and cap length.

    This is defense-in-depth. Description sanitization also happens at
    ingest, but the reranker gets noisy, scraped text; we re-trim here so
    one forgotten sanitize step upstream can't blow the token budget or
    leak HTML into the prompt.
    """
    if not text:
        return ""
    # Collapse HTML tags and whitespace. Not a general-purpose sanitizer;
    # just enough to keep the prompt clean. Untrusted content is bounded
    # by length anyway.
    stripped = re.sub(r"<[^>]+>", " ", text)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return stripped[:DESCRIPTION_CHAR_BUDGET]


def _build_prompt(
    target_titles: Sequence[str],
    top_skills: Sequence[str],
    candidates: Sequence[RerankCandidate],
) -> str:
    """Build the user prompt. Keeps the schema narrow so parsing is cheap."""
    titles = ", ".join(t for t in target_titles if t) or "(none provided)"
    skills = ", ".join(s for s in top_skills if s) or "(none provided)"
    lines: List[str] = [
        f"Target titles: {titles}",
        f"Top skills: {skills}",
        "",
        "Jobs:",
    ]
    for c in candidates:
        company = c.company or "Unknown"
        # Keep the label tight and deterministic so the model doesn't
        # paraphrase fields back at us.
        lines.append(
            f"- job_id={c.job_id} | title={c.title} | company={company} | "
            f"description={_trim_description(c.description)}"
        )
    lines.extend(
        [
            "",
            "Respond with STRICT JSON only:",
            '[{"job_id":"...","score":0-100,"reason":"..."}]',
        ]
    )
    return "\n".join(lines)


def _extract_json_array(raw: str) -> Optional[list]:
    """Parse a JSON array out of the model's output, tolerating code fences.

    Returns ``None`` on any parse/shape failure so the caller can fall back
    cleanly. We intentionally DO NOT try to hand-fix the JSON — if the
    model can't hit the schema, we'd rather trust ``semantic_fit`` than
    ship a creatively-patched version of someone's LLM output.
    """
    if not raw:
        return None
    text = raw.strip()
    # Strip triple-backtick fences if the model ignored the instruction.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    # Find the first '[' through the last ']' — safest way to ignore
    # stray "Sure, here you go:" preambles if the model emitted any.
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    blob = text[start : end + 1]
    try:
        parsed = json.loads(blob)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None
    return parsed


def _coerce_scores(
    raw_items: Iterable[Mapping],
    allowed_ids: set[str],
) -> List[RerankedScore]:
    """Validate and coerce the model output into ``RerankedScore`` rows.

    Silently drops items that:
      - lack ``job_id``, ``score``, or ``reason``
      - reference a job_id we never sent (hallucinations)
      - have out-of-range scores
      - repeat an already-seen job_id (first wins)
    """
    seen: set[str] = set()
    out: List[RerankedScore] = []
    for item in raw_items:
        if not isinstance(item, Mapping):
            continue
        jid = item.get("job_id")
        score = item.get("score")
        reason = item.get("reason")
        if not isinstance(jid, str) or jid in seen or jid not in allowed_ids:
            continue
        try:
            score_f = float(score)
        except (TypeError, ValueError):
            continue
        if not (SCORE_MIN <= score_f <= SCORE_MAX):
            continue
        reason_str = ""
        if isinstance(reason, str):
            words = reason.split()
            if len(words) > REASON_WORD_BUDGET:
                words = words[:REASON_WORD_BUDGET]
            reason_str = " ".join(words).strip()
        seen.add(jid)
        out.append(RerankedScore(job_id=jid, score=score_f, reason=reason_str))
    return out


async def rerank_candidates(
    *,
    target_titles: Sequence[str],
    top_skills: Sequence[str],
    candidates: Sequence[RerankCandidate],
    user_id: Optional[str] = None,
) -> Optional[List[RerankedScore]]:
    """Run the LLM reranker.

    Returns a list of :class:`RerankedScore` on success, or ``None`` if the
    reranker could not produce a trustworthy response. The caller MUST
    treat ``None`` as "keep the current ``semantic_fit`` ordering" — do
    NOT substitute a default score.

    Budget: one call per invocation. The :class:`ModelRouter` handles
    provider selection and cost tracking.
    """
    if not candidates:
        return []
    if len(candidates) > MAX_CANDIDATES:
        logger.info(
            "Reranker input trimmed to top-%d (received %d).",
            MAX_CANDIDATES,
            len(candidates),
        )
        candidates = list(candidates)[:MAX_CANDIDATES]

    prompt = _build_prompt(target_titles, top_skills, candidates)
    router = get_model_router()
    timeout = max(1.0, float(settings.AI_RERANK_TIMEOUT_SECONDS))

    started = time.monotonic()
    try:
        raw = await asyncio.wait_for(
            router.generate(
                task_type=TaskType.RERANK,
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                preferred_provider=settings.AI_RERANK_PROVIDER,
                user_id=user_id,
                # Deterministic scoring beats creative scoring here.
                temperature=0.2,
                max_tokens=4096,
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "Reranker timed out after %.1fs (batch=%d, user=%s)",
            timeout,
            len(candidates),
            user_id,
        )
        return None
    except Exception as exc:  # noqa: BLE001 — router handles retries; we don't
        logger.warning("Reranker generate() raised: %r", exc)
        return None

    elapsed = time.monotonic() - started
    if not raw:
        logger.warning("Reranker returned empty output (batch=%d).", len(candidates))
        return None

    parsed = _extract_json_array(raw)
    if parsed is None:
        logger.warning(
            "Reranker JSON parse failed; falling back to semantic_fit. "
            "Elapsed=%.1fms, preview=%r",
            elapsed * 1000,
            raw[:200],
        )
        return None

    allowed_ids = {c.job_id for c in candidates}
    scores = _coerce_scores(parsed, allowed_ids)
    if len(scores) < MIN_ITEMS_FOR_VALID_RESPONSE and len(scores) < len(candidates):
        # Fewer than the required floor? Untrustworthy. Caller falls back.
        logger.warning(
            "Reranker returned only %d/%d usable rows; rejecting.",
            len(scores),
            len(candidates),
        )
        return None

    logger.info(
        "Reranker ok (batch=%d, kept=%d, elapsed_ms=%.1f)",
        len(candidates),
        len(scores),
        elapsed * 1000,
    )
    return scores
