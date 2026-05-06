from abc import ABC, abstractmethod

from openai import OpenAI


class BaseClient(ABC):
    """Base class for all API clients."""

    @abstractmethod
    def query(self, prompt: str, temperature: float = 0) -> str:
        ...

    def _check_html(self, content: str) -> str:
        """Detect HTML responses (gateway/proxy errors)."""
        stripped = content.strip().lower()
        if stripped.startswith("<!doctype") or stripped.startswith("<html"):
            raise RuntimeError("API returned HTML instead of JSON — check base URL and API key")
        return content


def _ensure_v1(base_url: str) -> str:
    """Ensure base URL has /v1 suffix for OpenAI-compatible APIs."""
    base_url = base_url.rstrip("/")
    if not base_url.endswith("/v1"):
        base_url += "/v1"
    return base_url


def _extract_chat_content(response) -> str:
    """Extract content from OpenAI chat completion response."""
    if isinstance(response, str):
        return response
    elif isinstance(response, dict):
        choices = response.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            return msg.get("content", "") or ""
        return ""
    else:
        return response.choices[0].message.content or ""


class OpenAIChatClient(BaseClient):
    """Client for OpenAI Chat Completions API (chat.completions.create)."""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.client = OpenAI(base_url=_ensure_v1(base_url), api_key=api_key)
        self.model = model

    def query(self, prompt: str, temperature: float = 0) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=500,
        )
        content = _extract_chat_content(response)
        return self._check_html(content)


class OpenAIResponsesClient(BaseClient):
    """Client for OpenAI Responses API (responses.create)."""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.client = OpenAI(base_url=_ensure_v1(base_url), api_key=api_key)
        self.model = model

    def query(self, prompt: str, temperature: float = 0) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            temperature=temperature,
            max_output_tokens=500,
        )
        content = response.output_text or ""
        return self._check_html(content)


class AnthropicClient(BaseClient):
    """Client for Anthropic Messages API (messages.create)."""

    def __init__(self, base_url: str, api_key: str, model: str):
        import anthropic

        kwargs = {"api_key": api_key}
        # Only set base_url if user provided a non-default value
        if base_url:
            base_url = base_url.rstrip("/")
            kwargs["base_url"] = base_url
        self.client = anthropic.Anthropic(**kwargs)
        self.model = model

    def query(self, prompt: str, temperature: float = 0) -> str:
        response = self.client.messages.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=500,
        )
        content = response.content[0].text if response.content else ""
        return self._check_html(content)


_API_TYPES = {
    "openai-chat": OpenAIChatClient,
    "openai-responses": OpenAIResponsesClient,
    "anthropic": AnthropicClient,
}

VALID_API_TYPES = list(_API_TYPES.keys())


def create_client(api_type: str, base_url: str, api_key: str, model: str) -> BaseClient:
    """Factory: create the right client based on --api-type."""
    cls = _API_TYPES.get(api_type)
    if cls is None:
        raise ValueError(
            f"Unknown api-type '{api_type}'. Valid types: {', '.join(VALID_API_TYPES)}"
        )
    return cls(base_url=base_url, api_key=api_key, model=model)


# Backward compatibility
ModelClient = OpenAIChatClient
