"""
LLM Provider — Unified interface for all language model backends.

Supports:
  - Ollama (local, private, no API keys needed)
  - Anthropic (Claude)
  - OpenAI (GPT)

Fallback chain: tries providers in order until one works.
Default order: ollama → anthropic → openai
Override with PRIMARY_LLM_PROVIDER in .env

Usage:
    from llm_provider import get_llm
    llm = get_llm()
    response = llm.chat("What should I do?", system="You are helpful.")
    
    # Check what's available
    from llm_provider import check_available_providers
    available = check_available_providers()
"""

import os
import time
from abc import ABC, abstractmethod
from typing import Optional
from loguru import logger


class LLMError(Exception):
    """Structured error for LLM failures."""
    def __init__(self, provider: str, message: str, retryable: bool = False):
        self.provider = provider
        self.retryable = retryable
        super().__init__(f"[{provider}] {message}")


class LLMProvider(ABC):
    """Base class for all LLM providers."""
    
    name: str = "base"
    default_timeout: int = 60  # seconds
    max_retries: int = 2
    
    @abstractmethod
    def chat(self, messages: list[dict], system: str = "", model: str = "", max_tokens: int = 2048) -> str:
        """Send a chat completion request."""
        ...
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is currently reachable."""
        ...
    
    def vision(self, image_path: str, prompt: str = "Describe this image.") -> Optional[str]:
        """Optional: describe an image. Override in providers that support it."""
        return None

    def _retry(self, fn, *args, **kwargs):
        """Retry a call with exponential backoff."""
        last_err = None
        for attempt in range(self.max_retries + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_err = e
                if attempt < self.max_retries:
                    wait = 2 ** attempt
                    logger.warning(f"{self.name}: attempt {attempt+1} failed ({e}), retrying in {wait}s...")
                    time.sleep(wait)
        raise LLMError(self.name, f"Failed after {self.max_retries+1} attempts: {last_err}", retryable=False)


class OllamaProvider(LLMProvider):
    """Local Ollama — fully private, no API keys."""
    
    name = "ollama"
    
    def __init__(self, model: str = "llama3.1:8b", vision_model: str = "llava"):
        self.model = model
        self.vision_model = vision_model
        self._client = None
        self._validated_models: set[str] = set()
    
    @property
    def client(self):
        if self._client is None:
            import ollama
            self._client = ollama
        return self._client
    
    def is_available(self) -> bool:
        try:
            import ollama
            ollama.list()
            return True
        except Exception:
            return False

    def _validate_model(self, model: str):
        """Check if model is downloaded, offer to pull if not."""
        if model in self._validated_models:
            return
        try:
            models = [m.get("name", m.get("model", "")) for m in self.client.list().get("models", [])]
            # Ollama model names can be "llama3.1:8b" or "llama3.1:latest"
            if not any(model in m or m.startswith(model.split(":")[0]) for m in models):
                logger.warning(f"Ollama model '{model}' not found locally. Available: {models}")
                raise LLMError(self.name, f"Model '{model}' not downloaded. Run: ollama pull {model}", retryable=False)
            self._validated_models.add(model)
        except LLMError:
            raise
        except Exception as e:
            logger.debug(f"Could not validate model: {e}")
    
    def chat(self, messages: list[dict], system: str = "", model: str = "", max_tokens: int = 2048) -> str:
        use_model = model or self.model
        self._validate_model(use_model)

        def _call():
            all_messages = []
            if system:
                all_messages.append({"role": "system", "content": system})
            all_messages.extend(messages)
            response = self.client.chat(model=use_model, messages=all_messages)
            return response["message"]["content"]
        
        return self._retry(_call)
    
    def vision(self, image_path: str, prompt: str = "Describe this image in detail.") -> Optional[str]:
        try:
            response = self.client.chat(
                model=self.vision_model,
                messages=[{
                    "role": "user",
                    "content": prompt,
                    "images": [image_path],
                }],
            )
            return response["message"]["content"]
        except Exception as e:
            logger.warning(f"Ollama vision failed: {e}")
            return None


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API."""
    
    name = "anthropic"
    
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic()
        return self._client
    
    def is_available(self) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY", ""))
    
    def chat(self, messages: list[dict], system: str = "", model: str = "", max_tokens: int = 2048) -> str:
        def _call():
            response = self.client.messages.create(
                model=model or self.model,
                max_tokens=max_tokens,
                system=system or "",
                messages=messages,
            )
            return response.content[0].text
        return self._retry(_call)
    
    def vision(self, image_path: str, prompt: str = "Describe this image in detail.") -> Optional[str]:
        import base64
        # File size guard (20MB max for Anthropic)
        file_size = os.path.getsize(image_path)
        if file_size > 20 * 1024 * 1024:
            logger.warning(f"Image too large ({file_size/1024/1024:.1f}MB > 20MB limit)")
            return None
        with open(image_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode()
        
        # Determine media type
        ext = image_path.lower().rsplit(".", 1)[-1]
        media_types = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp"}
        media_type = media_types.get(ext, "image/jpeg")
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": img_data}},
                        {"type": "text", "text": prompt},
                    ],
                }],
            )
            return response.content[0].text
        except Exception as e:
            logger.warning(f"Anthropic vision failed: {e}")
            return None


class OpenAIProvider(LLMProvider):
    """OpenAI GPT API."""
    
    name = "openai"
    
    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI()
        return self._client
    
    def is_available(self) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY", ""))
    
    def chat(self, messages: list[dict], system: str = "", model: str = "", max_tokens: int = 2048) -> str:
        def _call():
            all_messages = []
            if system:
                all_messages.append({"role": "system", "content": system})
            all_messages.extend(messages)
            response = self.client.chat.completions.create(
                model=model or self.model,
                max_tokens=max_tokens,
                messages=all_messages,
            )
            return response.choices[0].message.content
        return self._retry(_call)


# ── Provider Registry ─────────────────────────────

PROVIDERS = {
    "ollama": OllamaProvider,
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
}


def check_available_providers() -> dict[str, bool]:
    """Check which providers are currently available. Logs specifics on failure."""
    results = {}
    for name, cls in PROVIDERS.items():
        try:
            provider = cls()
            available = provider.is_available()
            results[name] = available
            if not available:
                logger.debug(f"Provider '{name}': not configured (missing API key or service)")
        except Exception as e:
            results[name] = False
            logger.debug(f"Provider '{name}': initialization failed — {e}")
    return results


def get_llm(preferred: str = "", fallback_chain: list[str] | None = None) -> LLMProvider:
    """
    Get an LLM provider with automatic fallback.
    
    Priority:
      1. `preferred` (if specified and available)
      2. PRIMARY_LLM_PROVIDER from env/config
      3. Fallback chain: ollama → anthropic → openai
    
    Returns the first available provider.
    Raises RuntimeError if nothing is available.
    """
    from config_loader import settings
    
    chain = fallback_chain or []
    
    # Build priority chain
    if preferred:
        chain = [preferred] + [p for p in chain if p != preferred]
    
    if not chain:
        primary = settings.primary_llm_provider
        if primary == "ollama" or settings.use_local_llm:
            chain = ["ollama", "anthropic", "openai"]
        elif primary == "anthropic":
            chain = ["anthropic", "ollama", "openai"]
        elif primary == "openai":
            chain = ["openai", "ollama", "anthropic"]
        else:
            chain = ["ollama", "anthropic", "openai"]
    
    for name in chain:
        if name not in PROVIDERS:
            continue
        try:
            provider = PROVIDERS[name](
                model=settings.primary_model if name != "ollama" else settings.local_model_name
            )
            if provider.is_available():
                logger.info(f"LLM provider: {name}")
                return provider
            else:
                logger.debug(f"Provider '{name}' not available, trying next...")
        except Exception as e:
            logger.debug(f"Provider '{name}' failed to initialize: {e}")
    
    raise RuntimeError(
        f"No LLM provider available. Tried: {chain}. "
        f"Install Ollama for local inference, or set ANTHROPIC_API_KEY / OPENAI_API_KEY."
    )
