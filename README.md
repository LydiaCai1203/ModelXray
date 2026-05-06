# ModelXray

Detect the real model behind any OpenAI-compatible API. Built for developers who suspect their API provider is serving a cheaper model than advertised.

English | [简体中文](README_CN.md)

## Install

```bash
pip install -e .
```

## Usage

```bash
modelxray --base-url https://api.openai.com --api-key sk-xxx --model gpt-4o
```

Quick mode (fewer probes, faster):

```bash
modelxray --base-url https://your-relay.com --api-key sk-xxx --model gpt-4o --mode quick
```

## API Types

Use `--api-type` (`-t`) to select the API protocol. Default is `openai-chat`.

| Type | SDK | Use for |
|------|-----|---------|
| `openai-chat` | OpenAI `chat.completions` | OpenAI, Azure, most relay providers |
| `openai-responses` | OpenAI `responses` | OpenAI Responses API |
| `anthropic` | Anthropic `messages` | Anthropic Claude models |

Examples:

```bash
# OpenAI Chat Completions (default)
modelxray -b https://api.openai.com -k sk-xxx -m gpt-4o

# OpenAI Responses API
modelxray -t openai-responses -b https://api.openai.com -k sk-xxx -m gpt-4o

# Anthropic
modelxray -t anthropic -b https://api.anthropic.com -k sk-ant-xxx -m claude-sonnet-4-6
```

> `/v1` is auto-appended for `openai-chat` and `openai-responses` if missing. For `anthropic`, the SDK manages the endpoint automatically.

## How it works

Sends 25 carefully crafted probes across 6 independent dimensions:

| Dimension | What it tests |
|-----------|---------------|
| Safety fingerprint | RLHF-induced refusal patterns unique to each model family |
| Identity / knowledge | Self-reported creator, training cutoff |
| Reasoning depth | Problems where weaker models predictably fail |
| Tokenizer behavior | Character counting, Unicode handling |
| Tokenizer version | Token count ratios and Unicode split differences between model versions |
| Output style | Default formatting preferences |

Responses are scored and aggregated with Bayesian weighting to produce a confidence ranking.

For `token_count` probes, the tool sends a fixed text and compares the API-reported `usage.prompt_tokens` against expected ranges — different tokenizer generations produce measurably different token counts for the same input.

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
Probes run: 25
```

## Supported models

GPT-3.5-turbo, GPT-4o, GPT-4o-mini, Claude 3 Opus, Claude 3.5 Sonnet, Claude Sonnet 4, Claude Opus 4.6/4.7, Claude Sonnet 4.6/4.7, Gemini 1.5 Pro, Gemini 2.0 Flash, Llama 3 (8B/70B), Qwen (7B/72B), DeepSeek V3/R1, Kimi K2.5/K2.6, Mistral 7B.

## Cost

Each detection run costs < $0.01 in API credits (25 probes × ~300 tokens average).

## AI Analysis

Optionally, you can specify an "analyst" model to generate a natural language interpretation of the detection results — helpful when confidence scores are ambiguous.

```bash
modelxray -b https://api.openai.com -k sk-xxx -m gpt-4o \
  --analyst-url https://api.openai.com \
  --analyst-key sk-xxx \
  --analyst-model gpt-4o
```

The analyst model can use a different API protocol from the target model via `--analyst-type`:

```bash
# Test target via Anthropic, but use OpenAI for analysis
modelxray -t anthropic -b https://api.anthropic.com -k sk-ant-xxx -m claude-sonnet-4-6 \
  --analyst-type openai-chat \
  --analyst-url https://api.openai.com \
  --analyst-key sk-xxx \
  --analyst-model gpt-4o
```

| Option | Description |
|--------|-------------|
| `--analyst-url` | Analyst model API base URL |
| `--analyst-key` | Analyst model API key |
| `--analyst-model` | Analyst model name |
| `--analyst-type` | API protocol for analyst (defaults to `--api-type`) |

> All three of `--analyst-url`, `--analyst-key`, `--analyst-model` must be provided together, or all omitted.

## Limitations

- Probe evasion: a provider who knows the probe contents can spoof responses. Keep your probe library private.
- Fine-tuned models may confuse family-level detection.
- New models require manual addition of expected responses to the probe YAML files.
