# ModelXray

Detect the real model behind any OpenAI-compatible API. Built for developers who suspect their API provider is serving a cheaper model than advertised.

English | [简体中文](README_CN.md)

## Install

```bash
pip install -e .
```

## Usage

```bash
modelxray --base-url https://api.openai.com/v1 --api-key sk-xxx --model gpt-4o
```

Quick mode (fewer probes, faster):

```bash
modelxray --base-url https://your-relay.com/v1 --api-key sk-xxx --model gpt-4o --mode quick
```

## How it works

Sends 20 carefully crafted probes across 5 independent dimensions:

| Dimension | What it tests |
|-----------|---------------|
| Safety fingerprint | RLHF-induced refusal patterns unique to each model family |
| Identity / knowledge | Self-reported creator, training cutoff |
| Reasoning depth | Problems where weaker models predictably fail |
| Tokenizer behavior | Character counting, Unicode handling |
| Output style | Default formatting preferences |

Responses are scored and aggregated with Bayesian weighting to produce a confidence ranking.

## Example output

```
╭─────────────────────────────╮
│ Claimed model: gpt-4o       │
╰─────────────────────────────╯

  Rank  Model               Confidence  Bar
  #1    claude-3-5-sonnet   72.0%       █████████████████████
  #2    claude-3-opus        15.0%       ████░░░░░░░░░░░░░░░░░
  #3    gpt-4o               8.0%        ██░░░░░░░░░░░░░░░░░░░

╭──────────── Verdict ─────────────╮
│ Likely: claude-3-5-sonnet (72%)  │
╰──────────────────────────────────╯
Probes run: 20
```

## Supported models

GPT-3.5-turbo, GPT-4o, GPT-4o-mini, Claude 3 Opus, Claude 3.5 Sonnet, Gemini 1.5 Pro, Gemini 2.0 Flash, Llama 3 (8B/70B), Qwen (7B/72B), DeepSeek V3/R1, Mistral 7B.

## Cost

Each detection run costs < $0.01 in API credits (20 probes × ~300 tokens average).

## Limitations

- Probe evasion: a provider who knows the probe contents can spoof responses. Keep your probe library private.
- Fine-tuned models may confuse family-level detection.
- New models require manual addition of expected responses to the probe YAML files.
