"""
Groq Provider Implementation
"""

from typing import Optional
from groq import AsyncGroq

from app.ai.base import AIProvider


class GroqProvider(AIProvider):
    """Groq provider for fast inference."""

    def __init__(self, api_key: str, model_name: str = "llama-2-70b-4096"):
        super().__init__(api_key, model_name)
        self.client = AsyncGroq(api_key=api_key)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate text using Groq."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens or 4096,
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
        """Generate streaming text using Groq."""
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
        # Groq pricing (very low cost)
        return {"input": 0.0001, "output": 0.0001}

    @property
    def max_tokens(self) -> int:
        """Maximum tokens."""
        return 32768  # Context window

    @property
    def supports_streaming(self) -> bool:
        """Groq supports streaming."""
        return True

