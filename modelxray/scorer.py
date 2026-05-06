import re
from dataclasses import dataclass, field


@dataclass
class ProbeResult:
    probe_id: str
    response: str
    scores: dict[str, float] = field(default_factory=dict)  # model_id -> score 0..1


def score_probe(probe: dict, response: str) -> ProbeResult:
    result = ProbeResult(probe_id=probe["id"], response=response)
    resp_lower = response.lower().strip()

    for model_id, expected in probe.get("expected", {}).items():
        if isinstance(expected, str):
            result.scores[model_id] = 1.0 if expected.lower() in resp_lower else 0.0
        elif isinstance(expected, dict):
            contains = expected.get("contains", [])
            not_contains = expected.get("not_contains", [])
            pattern = expected.get("pattern")
            score = 1.0
            for c in contains:
                if c.lower() not in resp_lower:
                    score = 0.0
                    break
            for nc in not_contains:
                if nc.lower() in resp_lower:
                    score = 0.0
                    break
            if pattern and not re.search(pattern, response, re.IGNORECASE):
                score = 0.0
            result.scores[model_id] = score

    return result


def aggregate(results: list[ProbeResult], probe_weights: dict[str, float]) -> dict[str, float]:
    """Bayesian-style weighted aggregation. Returns model_id -> confidence 0..1."""
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
