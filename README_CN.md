# ModelXray

检测任何 OpenAI 兼容 API 背后的真实模型。专为怀疑中转站"注水"的开发者打造。

[English](README.md) | 简体中文

## 安装

```bash
pip install -e .
```

## 使用

```bash
modelxray --base-url https://api.openai.com/v1 --api-key sk-xxx --model gpt-4o
```

快速模式（更少探针，更快速度）：

```bash
modelxray --base-url https://your-relay.com/v1 --api-key sk-xxx --model gpt-4o --mode quick
```

## 工作原理

通过 5 个独立维度的 20 个精心设计的探针：

| 维度 | 测试内容 |
|------|----------|
| 安全训练指纹 | 每个模型家族独特的 RLHF 拒绝模式 |
| 身份/知识 | 自我报告的创建者、训练截止日期 |
| 推理深度 | 弱模型会预测性失败的问题 |
| Tokenizer 行为 | 字符计数、Unicode 处理 |
| 输出风格 | 默认格式偏好 |

响应经过评分并使用贝叶斯加权聚合，产生置信度排名。

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
Probes run: 20
```

## 支持的模型

GPT-3.5-turbo, GPT-4o, GPT-4o-mini, Claude 3 Opus, Claude 3.5 Sonnet, Gemini 1.5 Pro, Gemini 2.0 Flash, Llama 3 (8B/70B), Qwen (7B/72B), DeepSeek V3/R1, Mistral 7B。

## 成本

每次检测运行成本 < $0.01（20 个探针 × 平均约 300 tokens）。

## 局限性

- **探针规避**：知道探针内容的提供商可以伪造响应。请保持探针库私密。
- **微调模型**：可能混淆家族级别的检测。
- **新模型**：需要手动添加预期响应到探针 YAML 文件。
