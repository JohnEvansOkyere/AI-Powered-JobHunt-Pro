"""
Google Gemini Provider Implementation
"""

from typing import Optional
import google.generativeai as genai

from app.ai.base import AIProvider


class GeminiProvider(AIProvider):
    """Google Gemini provider."""

    def __init__(self, api_key: str, model_name: str = "gemini-pro"):
        super().__init__(api_key, model_name)
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate text using Google Gemini."""
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens or 8192,
            **kwargs
        }

        response = await self.model.generate_content_async(
            full_prompt,
            generation_config=generation_config
        )

        return response.text

    async def generate_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ):
        """Generate streaming text using Google Gemini."""
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        generation_config = {
            "temperature": temperature,
            **kwargs
        }

        response = await self.model.generate_content_async(
            full_prompt,
            generation_config=generation_config,
            stream=True
        )

        async for chunk in response:
            if chunk.text:
                yield chunk.text

    @property
    def cost_per_token(self) -> dict:
        """Cost per 1K tokens (approximate)."""
        # Gemini Pro pricing
        return {"input": 0.0005, "output": 0.0015}

    @property
    def max_tokens(self) -> int:
        """Maximum tokens."""
        return 32768  # Gemini Pro context window

    @property
    def supports_streaming(self) -> bool:
        """Gemini supports streaming."""
        return True

