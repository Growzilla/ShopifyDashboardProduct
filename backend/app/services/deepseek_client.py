"""
DeepSeek API Client via OpenRouter - OpenAI-compatible wrapper.

Uses OpenAI SDK with OpenRouter's base URL for access to DeepSeek models.
"""
import asyncio
import json
import time
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class DeepSeekClient:
    """
    DeepSeek API client via OpenRouter using OpenAI SDK.

    OpenRouter provides OpenAI-compatible API with access to
    multiple AI models including DeepSeek.
    """

    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=self.OPENROUTER_BASE_URL,
        )
        self.model = settings.deepseek_model
        self.reasoner_model = settings.deepseek_reasoner_model

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4000,
        response_format: dict | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """
        Execute chat completion with DeepSeek via OpenRouter.

        Args:
            messages: List of message dicts with role and content
            model: Model to use (defaults to deepseek/deepseek-chat)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            response_format: Response format specification (e.g., {"type": "json_object"})
            max_retries: Maximum retry attempts on failure

        Returns:
            Dict with response content and metadata

        Raises:
            ValueError: If response parsing fails
            RuntimeError: If max retries exceeded
        """
        start_time = time.time()
        model = model or self.model

        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )

                # Extract data
                tokens_used = response.usage.total_tokens if response.usage else 0
                content = response.choices[0].message.content

                if not content:
                    raise ValueError("Empty response from DeepSeek")

                # Parse JSON if requested
                if response_format and response_format.get("type") == "json_object":
                    result = json.loads(content)
                else:
                    result = {"content": content}

                # Add metadata
                result["_metadata"] = {
                    "ai_provider": "deepseek_openrouter",
                    "ai_model": model,
                    "tokens_used": tokens_used,
                    "duration_ms": int((time.time() - start_time) * 1000),
                }

                logger.info(
                    "DeepSeek completion successful",
                    model=model,
                    tokens=tokens_used,
                    attempt=attempt + 1,
                )

                return result

            except json.JSONDecodeError as e:
                logger.warning(
                    "Failed to parse DeepSeek response",
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt == max_retries - 1:
                    raise ValueError(f"JSON parse error: {e}")

            except Exception as e:
                logger.error(
                    "DeepSeek API error",
                    attempt=attempt + 1,
                    error=str(e),
                    model=model,
                )
                if attempt == max_retries - 1:
                    raise

                # Exponential backoff
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError("Max retries exceeded")

    async def analyze_with_reasoning(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 8000,
    ) -> dict[str, Any]:
        """
        Use DeepSeek Reasoner model for complex analysis.

        Args:
            prompt: Analysis prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Dict with analysis result and metadata
        """
        return await self.chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert analyst. Provide detailed, logical reasoning.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            model=self.reasoner_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )


# Singleton instance
deepseek_client = DeepSeekClient()
