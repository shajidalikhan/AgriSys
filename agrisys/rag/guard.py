"""Hallucination Guard (LLM-as-a-Judge).

Fulfills §10.3:
Validates that generated agricultural responses are strictly grounded
in retrieved ICAR/FAO source passages. Scores factual alignment from 0.0 to 1.0.
Escalates to KCC webhook if score < 0.70.
"""

from typing import Any, Dict, List, Optional
import json
import logging
import re
from pydantic import BaseModel, Field
import httpx

from agrisys.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

JUDGE_PROMPT = """You are a hallucination detection judge for an agricultural advisory AI.
RESPONSE: {response}
RETRIEVED_SOURCES: {sources}
Score from 0.0 to 1.0:
- 1.0 = every factual claim is directly supported by retrieved sources
- 0.7 = mostly supported, minor inference
- 0.5 = half supported, some fabrication
- 0.0 = completely fabricated, not in sources

Return only valid JSON in this format:
{{"score": float, "unsupported_claims": [str], "verdict": "pass"|"escalate"}}
"""


class HallucinationVerdict(BaseModel):
    """Output schema from hallucination judge."""
    score: float = Field(..., ge=0.0, le=1.0)
    unsupported_claims: List[str] = Field(default_factory=list)
    verdict: str = Field(..., description="'pass' if score >= threshold else 'escalate'")
    raw_response: Optional[str] = None


class HallucinationGuard:
    """Evaluates response grounding against retrieved sources."""

    def __init__(
        self,
        llm_provider: Optional[BaseLLMProvider] = None,
        threshold: float = 0.70,
        escalate_webhook_url: Optional[str] = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.threshold = threshold
        self.escalate_webhook_url = escalate_webhook_url

    async def verify(
        self,
        response: str,
        sources: List[str],
    ) -> HallucinationVerdict:
        """Evaluate the factual grounding of response against sources."""
        sources_text = "\n\n---\n\n".join(sources) if sources else "[NO RETRIEVED SOURCES]"

        if not self.llm_provider:
            # Fallback heuristic judge when LLM provider is not provided or in local test mode
            return self._heuristic_judge(response, sources)

        prompt = JUDGE_PROMPT.format(response=response, sources=sources_text)
        messages = [{"role": "user", "content": prompt}]

        try:
            raw_eval = await self.llm_provider.complete(messages, temperature=0.0, max_tokens=512)
            # Parse JSON from response
            match = re.search(r"\{.*\}", raw_eval, flags=re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                score = float(data.get("score", 0.7))
                claims = data.get("unsupported_claims", [])
                verdict_str = "pass" if score >= self.threshold else "escalate"
                verdict = HallucinationVerdict(
                    score=score,
                    unsupported_claims=claims,
                    verdict=verdict_str,
                    raw_response=raw_eval,
                )
            else:
                verdict = self._heuristic_judge(response, sources)
        except Exception as e:
            logger.warning("LLM judge failed: %s; using heuristic fallback", e)
            verdict = self._heuristic_judge(response, sources)

        # Trigger escalation if below threshold
        if verdict.score < self.threshold:
            await self._escalate(response, sources, verdict)

        return verdict

    def _heuristic_judge(self, response: str, sources: List[str]) -> HallucinationVerdict:
        """Fast lexical overlap verification fallback."""
        if not sources or not any(s.strip() for s in sources):
            return HallucinationVerdict(
                score=0.5,
                unsupported_claims=["No source context provided for verification"],
                verdict="escalate",
            )

        stopwords = {
            "this", "that", "these", "those", "have", "has", "had", "with", "from",
            "should", "would", "could", "about", "according", "advice", "please",
            "local", "recommend", "recommended", "which", "where", "there", "their",
            "your", "farmer", "guidelines", "following"
        }

        resp_words = {w for w in re.findall(r"\b\w{4,}\b", response.lower()) if w not in stopwords}
        source_words = {w for w in re.findall(r"\b\w{4,}\b", " ".join(sources).lower()) if w not in stopwords}

        if not resp_words:
            return HallucinationVerdict(score=1.0, unsupported_claims=[], verdict="pass")

        overlap = resp_words.intersection(source_words)
        ratio = len(overlap) / len(resp_words)
        # Scale overlap to a reasonable score
        score = min(1.0, max(0.4, ratio * 1.25))
        verdict_str = "pass" if score >= self.threshold else "escalate"

        unsupported: List[str] = []
        if score < self.threshold:
            missing_keywords = list(resp_words - source_words)[:5]
            unsupported.append(f"Unverified terms: {', '.join(missing_keywords)}")

        return HallucinationVerdict(
            score=round(score, 2),
            unsupported_claims=unsupported,
            verdict=verdict_str,
        )

    async def _escalate(
        self,
        response: str,
        sources: List[str],
        verdict: HallucinationVerdict,
    ) -> None:
        """Escalate ungrounded response to KCC webhook if configured."""
        if not self.escalate_webhook_url:
            logger.info("Hallucination detected (score=%.2f), but no webhook URL configured.", verdict.score)
            return

        payload = {
            "alert": "POTENTIAL_HALLUCINATION",
            "score": verdict.score,
            "unsupported_claims": verdict.unsupported_claims,
            "response": response,
            "source_snippets": [s[:200] for s in sources],
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(self.escalate_webhook_url, json=payload)
        except Exception as e:
            logger.error("Failed to post hallucination escalation: %s", e)
