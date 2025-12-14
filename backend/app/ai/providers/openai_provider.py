"""
OpenAI Provider Implementation
"""

from typing import Optional
from openai import AsyncOpenAI

from app.ai.base import AIProvider


class OpenAIProvider(AIProvider):
    """OpenAI provider using GPT models."""

    def __init__(self, api_key: str, model_name: str = "gpt-4-turbo-preview"):
        super().__init__(api_key, model_name)
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate text using OpenAI."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        return response.choices[0].message.content

    async def generate_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ):
        """Generate streaming text using OpenAI."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stream = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            stream=True,
            **kwargs
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    @property
    def cost_per_token(self) -> dict:
        """Cost per 1K tokens (approximate)."""
        # GPT-4 Turbo pricing (as of 2024)
        return {"input": 0.01, "output": 0.03}

    @property
    def max_tokens(self) -> int:
        """Maximum tokens."""
        return 128000  # GPT-4 Turbo context window

    @property
    def supports_streaming(self) -> bool:
        """OpenAI supports streaming."""
        return True

