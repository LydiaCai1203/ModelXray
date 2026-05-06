# ModelXray

检测任何 OpenAI 兼容 API 背后的真实模型。专为怀疑中转站"注水"的开发者打造。

[English](README.md) | 简体中文

## 安装

```bash
pip install -e .
```

## 使用

```bash
modelxray --base-url https://api.openai.com --api-key sk-xxx --model gpt-4o
```

快速模式（更少探针，更快速度）：

```bash
modelxray --base-url https://your-relay.com --api-key sk-xxx --model gpt-4o --mode quick
```

## API 类型

使用 `--api-type`（`-t`）选择 API 协议。默认为 `openai-chat`。

| 类型 | SDK | 适用场景 |
|------|-----|----------|
| `openai-chat` | OpenAI `chat.completions` | OpenAI、Azure、大多数中转站 |
| `openai-responses` | OpenAI `responses` | OpenAI Responses API |
| `anthropic` | Anthropic `messages` | Anthropic Claude 模型 |

示例：

```bash
# OpenAI Chat Completions（默认）
modelxray -b https://api.openai.com -k sk-xxx -m gpt-4o

# OpenAI Responses API
modelxray -t openai-responses -b https://api.openai.com -k sk-xxx -m gpt-4o

# Anthropic
modelxray -t anthropic -b https://api.anthropic.com -k sk-ant-xxx -m claude-sonnet-4-6
```

> `openai-chat` 和 `openai-responses` 会自动补全 `/v1`。`anthropic` 类型由 SDK 自动管理端点。

## 工作原理

通过 6 个独立维度的 25 个精心设计的探针：

| 维度 | 测试内容 |
|------|----------|
| 安全训练指纹 | 每个模型家族独特的 RLHF 拒绝模式 |
| 身份/知识 | 自我报告的创建者、训练截止日期 |
| 推理深度 | 弱模型会预测性失败的问题 |
| Tokenizer 行为 | 字符计数、Unicode 处理 |
| Tokenizer 版本指纹 | 不同模型版本间的 token 计数比率和 Unicode 拆分差异 |
| 输出风格 | 默认格式偏好 |

响应经过评分并使用贝叶斯加权聚合，产生置信度排名。

对于 `token_count` 类型探针，工具会发送固定文本并对比 API 返回的 `usage.prompt_tokens` 与预期范围——不同代际的 tokenizer 对相同输入会产生可测量的 token 数差异。

## 输出示例

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

## 支持的模型

GPT-3.5-turbo, GPT-4o, GPT-4o-mini, Claude 3 Opus, Claude 3.5 Sonnet, Claude Sonnet 4, Claude Opus 4.6/4.7, Claude Sonnet 4.6/4.7, Gemini 1.5 Pro, Gemini 2.0 Flash, Llama 3 (8B/70B), Qwen (7B/72B), DeepSeek V3/R1, Kimi K2.5/K2.6, Mistral 7B。

## 成本

每次检测运行成本 < $0.01（25 个探针 × 平均约 300 tokens）。

## AI 解读

你可以指定一个"解读模型"来对检测结果生成自然语言分析报告——当置信度分布模糊时特别有用。

```bash
modelxray -b https://api.openai.com -k sk-xxx -m gpt-4o \
  --analyst-url https://api.openai.com \
  --analyst-key sk-xxx \
  --analyst-model gpt-4o
```

解读模型可以通过 `--analyst-type` 使用与被测模型不同的 API 协议：

```bash
# 用 Anthropic 协议测目标模型，用 OpenAI 做解读
modelxray -t anthropic -b https://api.anthropic.com -k sk-ant-xxx -m claude-sonnet-4-6 \
  --analyst-type openai-chat \
  --analyst-url https://api.openai.com \
  --analyst-key sk-xxx \
  --analyst-model gpt-4o
```

| 参数 | 说明 |
|------|------|
| `--analyst-url` | 解读模型的 API base URL |
| `--analyst-key` | 解读模型的 API key |
| `--analyst-model` | 解读模型名称 |
| `--analyst-type` | 解读模型的 API 协议（默认跟随 `--api-type`） |

> `--analyst-url`、`--analyst-key`、`--analyst-model` 三者必须同时提供或同时省略。

## 局限性

- **探针规避**：知道探针内容的提供商可以伪造响应。请保持探针库私密。
- **微调模型**：可能混淆家族级别的检测。
- **新模型**：需要手动添加预期响应到探针 YAML 文件。
