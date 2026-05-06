from openai import OpenAI


class ModelClient:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model

    def query(self, prompt: str, temperature: float = 0) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=500,
        )
        # Handle both standard OpenAI SDK response objects and raw dict/str responses
        if isinstance(response, str):
            return response
        if isinstance(response, dict):
            choices = response.get("choices", [])
            if choices:
                msg = choices[0].get("message", {})
                return msg.get("content", "") or ""
            return ""
        content = response.choices[0].message.content
        return content or ""
