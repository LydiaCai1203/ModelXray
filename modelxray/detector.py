import yaml
from pathlib import Path
from .client import BaseClient
from .scorer import score_probe, score_token_probe, aggregate, ProbeResult

PROBES_DIR = Path(__file__).parent.parent / "probes"


def load_probes(mode: str = "standard") -> list[dict]:
    probes = []
    for yaml_file in sorted(PROBES_DIR.rglob("*.yaml")):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
        if isinstance(data, list):
            probes.extend(data)
        else:
            probes.append(data)
    if mode == "quick":
        # Only high-weight probes
        probes = [p for p in probes if p.get("weight", 1.0) >= 1.5]
    return probes


def detect(client: BaseClient, mode: str = "standard") -> dict:
    probes = load_probes(mode)
    results: list[ProbeResult] = []
    weights = {}

    for probe in probes:
        try:
            probe_type = probe.get("type", "content")
            if probe_type == "token_count":
                response, usage = client.query_with_usage(probe["prompt"])
                result = score_token_probe(probe, response, usage)
            else:
                response = client.query(probe["prompt"])
                result = score_probe(probe, response)
            results.append(result)
            weights[probe["id"]] = probe.get("weight", 1.0)
        except Exception as e:
            results.append(ProbeResult(
                probe_id=probe["id"],
                response=f"ERROR: {e}",
                category=probe.get("category", ""),
            ))

    confidence = aggregate(results, weights, claimed_model=client.model)
    return {
        "confidence": confidence,
        "probe_results": results,
        "total_probes": len(probes),
    }
