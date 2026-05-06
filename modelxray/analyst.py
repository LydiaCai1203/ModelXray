from .client import BaseClient
from .scorer import ProbeResult


def _build_prompt(result: dict, claimed_model: str) -> str:
    """Build the analysis prompt from detection results."""
    confidence: dict[str, float] = result["confidence"]
    probe_results: list[ProbeResult] = result["probe_results"]
    total_probes: int = result["total_probes"]

    top_models = list(confidence.items())[:10]

    # Format confidence ranking
    ranking_lines = []
    for i, (model_id, conf) in enumerate(top_models):
        ranking_lines.append(f"  #{i+1} {model_id}: {conf*100:.1f}%")
    ranking_text = "\n".join(ranking_lines)

    # Format probe evidence
    evidence_lines = []
    for r in probe_results:
        if r.response.startswith("ERROR:"):
            continue
        # Top 3 scoring models for this probe
        top_scores = sorted(r.scores.items(), key=lambda x: -x[1])[:3]
        scores_text = ", ".join(f"{m}: {s:.1f}" for m, s in top_scores)
        response_preview = r.response.split("\n")[0].strip()[:80]
        evidence_lines.append(
            f"  - probe: {r.probe_id} | category: {r.category or 'other'}\n"
            f"    response: \"{response_preview}\"\n"
            f"    scores: [{scores_text}]"
        )
    evidence_text = "\n".join(evidence_lines) if evidence_lines else "  (no valid probe responses)"

    return f"""\
你是一位 API 模型鉴定专家。请根据以下探针检测数据，分析被测模型的真实身份。

## 输入信息

声称的模型名称: {claimed_model}
探针总数: {total_probes}

### 置信度排名 (Top 10)
{ranking_text}

### 探针证据
{evidence_text}

## 分析要求

请用简洁的自然语言完成以下分析：

1. **结论**: 被测模型最可能的真实身份是什么？与声称的模型名是否一致？
2. **关键证据**: 哪些探针提供了最有力的证据？为什么？
3. **置信度解读**: 当前的置信度分布意味着什么？(例如：所有模型都在 5-6% 说明什么？某个模型远超其他说明什么？)
4. **注意事项**: 是否存在可疑的异常？是否有足够的证据支撑结论？

请直接输出分析内容，不要重复输入数据。"""


def analyze(client: BaseClient, result: dict, claimed_model: str) -> str:
    """Call the analyst model to generate a natural language analysis report."""
    prompt = _build_prompt(result, claimed_model)
    return client.query(prompt, max_tokens=2048)
