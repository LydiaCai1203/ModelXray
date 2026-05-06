import base64
import mimetypes
import yaml
from pathlib import Path
from .client import BaseClient
from .scorer import score_probe, score_token_probe, aggregate, ProbeResult

PROBES_DIR = Path(__file__).parent.parent / "probes"

# Cache for loaded images: image_path -> (base64_data, media_type)
_image_cache: dict[str, tuple[str, str]] = {}


def _load_image_b64(image_name: str) -> tuple[str, str]:
    """Load image from probes directory, return (base64_data, media_type)."""
    if image_name in _image_cache:
        return _image_cache[image_name]

    # Search in probes directory tree
    matches = list(PROBES_DIR.rglob(image_name))
    if not matches:
        raise FileNotFoundError(f"Image '{image_name}' not found under {PROBES_DIR}")
    image_path = matches[0]

    media_type = mimetypes.guess_type(str(image_path))[0] or "image/png"
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    _image_cache[image_name] = (b64, media_type)
    return b64, media_type


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


def _run_vision_probes(
    client: BaseClient,
    vision_probes: list[dict],
) -> list[tuple[dict, ProbeResult]]:
    """Run vision probes sequentially by level, stop early if a level fails."""
    # Sort by level
    vision_probes.sort(key=lambda p: p.get("level", 0))

    results: list[tuple[dict, ProbeResult]] = []
    failed_level = None

    for probe in vision_probes:
        level = probe.get("level", 0)

        # Early termination: if a previous level failed, skip higher levels
        if failed_level is not None and level > failed_level:
            result = ProbeResult(
                probe_id=probe["id"],
                response=f"SKIPPED: Level {failed_level} failed",
                category=probe.get("category", ""),
            )
            results.append((probe, result))
            continue

        try:
            image_name = probe["image"]
            b64, media_type = _load_image_b64(image_name)
            response = client.query_vision(
                prompt=probe["prompt"],
                image_base64=b64,
                media_type=media_type,
            )
            result = score_probe(probe, response)

            # Check if this level passed for any model
            has_any_match = any(s > 0 for s in result.scores.values())
            if not has_any_match and result.scores:
                failed_level = level

            results.append((probe, result))
        except NotImplementedError:
            # Client doesn't support vision — skip all vision probes
            result = ProbeResult(
                probe_id=probe["id"],
                response="SKIPPED: Client does not support vision",
                category=probe.get("category", ""),
            )
            results.append((probe, result))
            break
        except Exception as e:
            result = ProbeResult(
                probe_id=probe["id"],
                response=f"ERROR: {e}",
                category=probe.get("category", ""),
            )
            results.append((probe, result))
            failed_level = level

    return results


def detect(client: BaseClient, mode: str = "standard") -> dict:
    probes = load_probes(mode)
    results: list[ProbeResult] = []
    weights = {}

    # Separate vision probes from text probes
    text_probes = [p for p in probes if p.get("type") != "vision"]
    vision_probes = [p for p in probes if p.get("type") == "vision"]

    # Run text probes
    for probe in text_probes:
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

    # Run vision probes (sequential, with early termination)
    if vision_probes:
        vision_results = _run_vision_probes(client, vision_probes)
        for probe, result in vision_results:
            results.append(result)
            weights[probe["id"]] = probe.get("weight", 1.0)

    confidence = aggregate(results, weights, claimed_model=client.model)
    return {
        "confidence": confidence,
        "probe_results": results,
        "total_probes": len(probes),
    }
