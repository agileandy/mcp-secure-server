"""AI client interfaces for figma-stories-plugin.

This module provides abstract interfaces and implementations for AI providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import UserStory


@dataclass
class AIResponse:
    """Response from an AI API call."""

    text: str
    model: str
    tokens_used: int
    finish_reason: str


class AIClientBase(ABC):
    """Abstract base class for AI providers.

    Subclasses must implement all methods for specific AI providers.
    """

    @abstractmethod
    async def generate_story_title(
        self,
        component_name: str,
        context: str,
    ) -> str:
        pass

    @abstractmethod
    async def generate_story_description(
        self,
        component_name: str,
        context: str,
        text_content: str,
    ) -> str:
        pass

    @abstractmethod
    async def generate_acceptance_criteria(
        self,
        text_content: str,
        annotations: list[str],
        variants: list[str],
    ) -> str:
        pass

    @abstractmethod
    async def enhance_story(
        self,
        story: UserStory,
        instructions: str,
    ) -> UserStory:
        pass


class NoOpAIClient(AIClientBase):
    """No-op AI client for when AI is disabled."""

    async def generate_story_title(
        self,
        component_name: str,
        context: str,
    ) -> str:
        return component_name

    async def generate_story_description(
        self,
        component_name: str,
        context: str,
        text_content: str,
    ) -> str:
        return (
            f"As a user, I want to interact with {component_name}, so that I can achieve my goals."
        )

    async def generate_acceptance_criteria(
        self,
        text_content: str,
        annotations: list[str],
        variants: list[str],
    ) -> str:
        return ""

    async def enhance_story(
        self,
        story: UserStory,
        instructions: str,
    ) -> UserStory:
        return story


class OpenRouterClient(AIClientBase):
    """OpenRouter AI client for nvidia/nemotron-3-nano-30b-a3b:free and other models."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "nvidia/nemotron-3-nano-30b-a3b:free",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        timeout: int = 60,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    async def generate_story_title(
        self,
        component_name: str,
        context: str,
    ) -> str:
        prompt = f"""You are an expert agile product manager. Generate a concise, action-oriented user story title for a Figma component.

Component: {component_name}
Context: {context}

Output only the title, no markdown formatting."""

        response = await self._call_api(prompt)
        return response.text.strip()

    async def generate_story_description(
        self,
        component_name: str,
        context: str,
        text_content: str,
    ) -> str:
        prompt = f"""You are an expert agile product manager. Generate a user story description in the format: "As a [role], I want to [action], so that [benefit]".

Component: {component_name}
Context: {context}
Text: {text_content[:200]}

Output only the description sentence, no markdown formatting."""

        response = await self._call_api(prompt)
        return response.text.strip()

    async def generate_acceptance_criteria(
        self,
        text_content: str,
        annotations: list[str],
        variants: list[str],
    ) -> str:
        prompt = f"""You are an expert QA engineer. Generate Given/When/Then acceptance criteria.

Text: {text_content[:300]}
Annotations: {", ".join(annotations) if annotations else "None"}
Variants: {", ".join(variants) if variants else "None"}

Generate 3-5 acceptance criteria. Format:
Given [initial state]
When [user action]
Then [expected outcome]

Separate criteria with blank lines. Only output the criteria."""

        response = await self._call_api(prompt)
        return response.text

    async def enhance_story(
        self,
        story: UserStory,
        instructions: str,
    ) -> UserStory:
        from .models import AcceptanceCriteria

        prompt = f"""You are an expert agile product manager. Enhance this user story.

Current Story:
Title: {story.title}
Description: {story.description}
Acceptance Criteria: {story.acceptance_criteria}

Instructions: {instructions}

Enhance the acceptance criteria to be more specific and testable. Keep the same format.
Add 2-3 additional criteria if needed."""

        response = await self._call_api(prompt)

        criteria = []
        for line in response.text.strip().split("\n\n"):
            if "Given" in line or "When" in line or "Then" in line:
                parts = self._parse_criteria(line)
                if parts:
                    criteria.append(AcceptanceCriteria(*parts))

        story.acceptance_criteria = criteria
        return story

    async def _call_api(self, prompt: str) -> AIResponse:
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "figma-stories-plugin",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.base_url,
                headers=headers,
                json=payload,
            )

            if response.status_code != 200:
                raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")

            data = response.json()

            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            text = message.get("content", "")

            return AIResponse(
                text=text,
                model=self.model,
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                finish_reason=choice.get("finish_reason", "stop"),
            )

    def _parse_criteria(self, text: str) -> tuple | None:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        given = ""
        when_action = ""
        then_outcome = ""

        for line in lines:
            line_lower = line.lower()
            if line_lower.startswith("given"):
                given = line[6:].strip() if len(line) > 6 else line
            elif line_lower.startswith("when"):
                when_action = line[5:].strip() if len(line) > 5 else line
            elif line_lower.startswith("then"):
                then_outcome = line[5:].strip() if len(line) > 5 else line

        if given and when_action and then_outcome:
            return (given, when_action, then_outcome)

        return None


class OpenAIClient(OpenRouterClient):
    """OpenAI-compatible API client."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        timeout: int = 60,
    ):
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )


def create_ai_client(config) -> AIClientBase | None:
    """Create an AI client based on configuration."""
    if not config.ai.enabled or not config.ai.api_key:
        return NoOpAIClient()

    provider = config.ai.provider.lower()

    if provider == "openrouter":
        return OpenRouterClient(
            api_key=config.ai.api_key,
            base_url=config.ai.endpoint,
            model=config.ai.model,
            temperature=config.ai.temperature,
            max_tokens=config.ai.max_tokens,
            timeout=config.ai.timeout,
        )
    elif provider in ("openai", "azure"):
        return OpenAIClient(
            api_key=config.ai.api_key,
            base_url=config.ai.endpoint,
            model=config.ai.model,
            temperature=config.ai.temperature,
            max_tokens=config.ai.max_tokens,
            timeout=config.ai.timeout,
        )
    else:
        return NoOpAIClient()
