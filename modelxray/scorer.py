import re
from dataclasses import dataclass, field


@dataclass
class ProbeResult:
    probe_id: str
    response: str
    scores: dict[str, float] = field(default_factory=dict)  # model_id -> score 0..1
    category: str = ""


def _eval_expected(expected: dict | str, response: str) -> float:
    resp_lower = response.lower().strip()
    if isinstance(expected, str):
        return 1.0 if expected.lower() in resp_lower else 0.0
    contains = expected.get("contains", [])
    not_contains = expected.get("not_contains", [])
    pattern = expected.get("pattern")
    for c in contains:
        if c.lower() not in resp_lower:
            return 0.0
    for nc in not_contains:
        if nc.lower() in resp_lower:
            return 0.0
    if pattern and not re.search(pattern, response, re.IGNORECASE):
        return 0.0
    return 1.0


def score_probe(probe: dict, response: str) -> ProbeResult:
    result = ProbeResult(
        probe_id=probe["id"],
        response=response,
        category=probe.get("category", ""),
    )
    for model_id, expected in probe.get("expected", {}).items():
        result.scores[model_id] = _eval_expected(expected, response)
    return result


def score_token_probe(probe: dict, response: str, usage: dict) -> ProbeResult:
    """Score a token_count probe using prompt_tokens from API usage data."""
    prompt_tokens = usage.get("prompt_tokens")
    result = ProbeResult(
        probe_id=probe["id"],
        response=response,
        category=probe.get("category", ""),
    )
    if prompt_tokens is None:
        # No usage data — can't score, leave scores empty
        return result
    for model_id, expected in probe.get("expected", {}).items():
        result.scores[model_id] = _eval_token_range(expected, prompt_tokens)
    result.response = f"prompt_tokens={prompt_tokens}"
    return result


def _eval_token_range(expected: dict | list, prompt_tokens: int) -> float:
    """Evaluate whether prompt_tokens falls within expected token_range [min, max]."""
    if isinstance(expected, dict):
        token_range = expected.get("token_range")
    elif isinstance(expected, list) and len(expected) == 2:
        token_range = expected
    else:
        return 0.0
    if not token_range or len(token_range) != 2:
        return 0.0
    lo, hi = token_range
    return 1.0 if lo <= prompt_tokens <= hi else 0.0


# Canonical family tokens extracted from model names
_FAMILY_TOKENS = {
    "gpt", "claude", "gemini", "llama", "qwen", "deepseek", "mistral",
    "kimi", "moonshot",
    "opus", "sonnet", "haiku", "flash", "pro", "turbo", "mini", "nano",
    "o1", "o3", "o4",
    "k2", "k2.5", "k2.6",
}


def _tokenize_model(name: str) -> set[str]:
    """Split model name into matchable tokens: 'claude-opus-4-6' -> {'claude', 'opus'}"""
    parts = re.split(r'[-_.\s]+', name.lower())
    return {p for p in parts if p in _FAMILY_TOKENS}


def _best_key(probe_keys: list[str], candidate: str) -> str | None:
    """Return the probe key that best matches candidate model name by token overlap."""
    c = candidate.lower()
    # Exact match first
    for k in probe_keys:
        if k.lower() == c:
            return k
    # Token overlap matching
    c_tokens = _tokenize_model(candidate)
    if not c_tokens:
        return None
    best, best_score = None, 0
    for k in probe_keys:
        k_tokens = _tokenize_model(k)
        overlap = len(c_tokens & k_tokens)
        if overlap > best_score:
            best, best_score = k, overlap
    return best if best_score > 0 else None


def aggregate(
    results: list[ProbeResult],
    probe_weights: dict[str, float],
    claimed_model: str = "",
) -> dict[str, float]:
    """Weighted aggregation. Returns model_id -> confidence 0..1, sorted descending."""
    totals: dict[str, float] = {}
    weight_sum: dict[str, float] = {}

    for r in results:
        w = probe_weights.get(r.probe_id, 1.0)
        for model_id, score in r.scores.items():
            totals[model_id] = totals.get(model_id, 0.0) + score * w
            weight_sum[model_id] = weight_sum.get(model_id, 0.0) + w

    raw = {m: totals[m] / weight_sum[m] for m in totals if weight_sum[m] > 0}
    total = sum(raw.values()) or 1.0
    return {m: v / total for m, v in sorted(raw.items(), key=lambda x: -x[1])}
