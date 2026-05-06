from abc import ABC, abstractmethod

from openai import OpenAI


class BaseClient(ABC):
    """Base class for all API clients."""

    @abstractmethod
    def query(self, prompt: str, temperature: float = 0, max_tokens: int = 500) -> str:
        ...

    def query_with_usage(self, prompt: str, temperature: float = 0) -> tuple[str, dict]:
        """Query and return (content, usage_dict).

        usage_dict has keys: prompt_tokens, completion_tokens, total_tokens.
        Subclasses may override for native usage support.
        Returns empty usage dict if not available.
        """
        content = self.query(prompt, temperature)
        return content, {}

    def query_vision(
        self, prompt: str, image_base64: str, media_type: str = "image/png",
        temperature: float = 0, max_tokens: int = 1024,
    ) -> str:
        """Query with an image (base64-encoded). Subclasses override for native vision."""
        raise NotImplementedError("This client does not support vision queries")

    def _check_html(self, content: str) -> str:
        """Detect HTML responses (gateway/proxy errors)."""
        stripped = content.strip().lower()
        if stripped.startswith("<!doctype") or stripped.startswith("<html"):
            raise RuntimeError("API returned HTML instead of JSON — check base URL and API key")
        return content


def _ensure_v1(base_url: str) -> str:
    """Ensure base URL has /v1 suffix for standard OpenAI endpoints.

    Only auto-appends /v1 for known OpenAI-compatible hosts.
    Custom gateways / proxies are left as-is.
    """
    base_url = base_url.rstrip("/")
    from urllib.parse import urlparse

    host = urlparse(base_url).hostname or ""
    known_hosts = {"api.openai.com", "api.moonshot.cn", "api.deepseek.com"}
    if host in known_hosts and not base_url.endswith("/v1"):
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

    def _call(self, prompt: str, temperature: float = 0, max_tokens: int = 500):
        return self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def query(self, prompt: str, temperature: float = 0, max_tokens: int = 500) -> str:
        response = self._call(prompt, temperature, max_tokens)
        content = _extract_chat_content(response)
        return self._check_html(content)

    def query_with_usage(self, prompt: str, temperature: float = 0) -> tuple[str, dict]:
        response = self._call(prompt, temperature)
        content = _extract_chat_content(response)
        content = self._check_html(content)
        usage = {}
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        return content, usage

    def query_vision(
        self, prompt: str, image_base64: str, media_type: str = "image/png",
        temperature: float = 0, max_tokens: int = 1024,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_base64}"}},
                    {"type": "text", "text": prompt},
                ],
            }],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = _extract_chat_content(response)
        return self._check_html(content)


class OpenAIResponsesClient(BaseClient):
    """Client for OpenAI Responses API (responses.create)."""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.client = OpenAI(base_url=_ensure_v1(base_url), api_key=api_key)
        self.model = model

    def _call(self, prompt: str, temperature: float = 0, max_tokens: int = 500):
        return self.client.responses.create(
            model=self.model,
            input=prompt,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

    def query(self, prompt: str, temperature: float = 0, max_tokens: int = 500) -> str:
        response = self._call(prompt, temperature, max_tokens)
        content = response.output_text or ""
        return self._check_html(content)

    def query_with_usage(self, prompt: str, temperature: float = 0) -> tuple[str, dict]:
        response = self._call(prompt, temperature)
        content = response.output_text or ""
        content = self._check_html(content)
        usage = {}
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": (response.usage.input_tokens or 0) + (response.usage.output_tokens or 0),
            }
        return content, usage

    def query_vision(
        self, prompt: str, image_base64: str, media_type: str = "image/png",
        temperature: float = 0, max_tokens: int = 1024,
    ) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_image", "image_url": f"data:{media_type};base64,{image_base64}"},
                    {"type": "input_text", "text": prompt},
                ],
            }],
            temperature=temperature,
            max_output_tokens=max_tokens,
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

    def _call(self, prompt: str, temperature: float = 0, max_tokens: int = 500):
        return self.client.messages.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def query(self, prompt: str, temperature: float = 0, max_tokens: int = 500) -> str:
        response = self._call(prompt, temperature, max_tokens)
        content = response.content[0].text if response.content else ""
        return self._check_html(content)

    def query_with_usage(self, prompt: str, temperature: float = 0) -> tuple[str, dict]:
        response = self._call(prompt, temperature)
        content = response.content[0].text if response.content else ""
        content = self._check_html(content)
        usage = {}
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": (response.usage.input_tokens or 0) + (response.usage.output_tokens or 0),
            }
        return content, usage

    def query_vision(
        self, prompt: str, image_base64: str, media_type: str = "image/png",
        temperature: float = 0, max_tokens: int = 1024,
    ) -> str:
        response = self.client.messages.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_base64}},
                    {"type": "text", "text": prompt},
                ],
            }],
            temperature=temperature,
            max_tokens=max_tokens,
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
