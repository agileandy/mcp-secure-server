"""Configuration management for figma-stories-plugin.

This module handles loading and validation of configuration from
YAML files and environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class AIConfig:
    """AI configuration settings."""

    enabled: bool = False
    provider: str = "openrouter"
    endpoint: str = "https://openrouter.ai/api/v1"
    model: str = "nvidia/nemotron-3-nano-30b-a3b:free"
    api_key: str = ""
    temperature: float = 0.3
    max_tokens: int = 2000
    timeout: int = 60

    def validate(self) -> None:
        """Validate AI configuration."""
        if self.enabled:
            if not self.endpoint:
                raise ValueError("AI endpoint is required when AI is enabled")
            if not self.model:
                raise ValueError("AI model is required when AI is enabled")


@dataclass
class OutputConfig:
    """Output configuration settings."""

    directory: Path = Path.cwd()
    filename_pattern: str = "{design_title}_user_stories.md"
    append_mode: bool = False

    def get_output_path(self, design_title: str, filename: str | None = None) -> Path:
        """Get the output path for generated stories."""
        if filename:
            return self.directory / filename

        safe_title = "".join(
            c if c.isalnum() or c in (" ", "-", "_") else "_" for c in design_title
        ).strip()
        safe_title = safe_title.replace(" ", "-")

        filename = self.filename_pattern.format(design_title=safe_title)
        return self.directory / filename


@dataclass
class StoryGenerationConfig:
    """Story generation configuration settings."""

    include_components: bool = True
    include_text_content: bool = True
    include_annotations: bool = True
    include_comments: bool = True
    include_component_variants: bool = True
    epic_source: str = "page_name"
    template_format: str = "given_when_then"
    interactive_mode: bool = True


@dataclass
class FigmaStoriesConfig:
    """Main configuration for figma-stories-plugin."""

    figma_api_token: str = ""
    ai: AIConfig = field(default_factory=AIConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    story_generation: StoryGenerationConfig = field(default_factory=StoryGenerationConfig)

    @classmethod
    def load_from_file(cls, config_path: Path) -> FigmaStoriesConfig:
        """Load configuration from YAML file."""
        if not config_path.exists():
            return cls()

        with open(config_path) as f:
            raw_config = yaml.safe_load(f) or {}

        return cls._parse_config(raw_config)

    @classmethod
    def _parse_config(cls, raw_config: dict) -> FigmaStoriesConfig:
        """Parse raw configuration dictionary."""
        figma_config = raw_config.get("figma", {})
        ai_config = raw_config.get("ai", {})
        output_config = raw_config.get("output", {})
        story_config = raw_config.get("story_generation", {})

        figma_api_token = cls._resolve_env_var(figma_config.get("api_token", ""))

        ai = AIConfig(
            enabled=ai_config.get("enabled", False),
            provider=ai_config.get("provider", "openrouter"),
            endpoint=cls._resolve_env_var(ai_config.get("endpoint", "")),
            model=ai_config.get("model", "nvidia/nemotron-3-nano-30b-a3b:free"),
            api_key=cls._resolve_env_var(ai_config.get("api_key", "")),
            temperature=ai_config.get("temperature", 0.3),
            max_tokens=ai_config.get("max_tokens", 2000),
            timeout=ai_config.get("timeout", 60),
        )

        output = OutputConfig(
            directory=Path(
                cls._resolve_env_var(output_config.get("directory", "${PWD}")).replace(
                    "${PWD}", str(Path.cwd())
                )
            ),
            filename_pattern=output_config.get(
                "filename_pattern", "{design_title}_user_stories.md"
            ),
            append_mode=output_config.get("append_mode", False),
        )

        story_generation = StoryGenerationConfig(
            include_components=story_config.get("include_components", True),
            include_text_content=story_config.get("include_text_content", True),
            include_annotations=story_config.get("include_annotations", True),
            include_comments=story_config.get("include_comments", True),
            include_component_variants=story_config.get("include_component_variants", True),
            epic_source=story_config.get("epic_source", "page_name"),
            template_format=story_config.get("template_format", "given_when_then"),
            interactive_mode=story_config.get("interactive_mode", True),
        )

        return cls(
            figma_api_token=figma_api_token,
            ai=ai,
            output=output,
            story_generation=story_generation,
        )

    @staticmethod
    def _resolve_env_var(value: str) -> str:
        """Resolve environment variable references in config values.

        Supports ${VAR_NAME} syntax for environment variables.
        """
        if not isinstance(value, str):
            return value

        if value.startswith("${") and value.endswith("}"):
            var_name = value[2:-1]
            return os.environ.get(var_name, "")

        return value

    def validate(self) -> None:
        """Validate configuration."""
        if not self.figma_api_token:
            raise ValueError(
                "Figma API token is required. "
                "Set FIGMA_API_TOKEN environment variable or "
                "configure in figma_stories.yaml"
            )

        self.ai.validate()

    def is_ai_enabled(self) -> bool:
        """Check if AI features are enabled."""
        return self.ai.enabled and bool(self.ai.api_key)

    @classmethod
    def from_environment(cls) -> FigmaStoriesConfig:
        """Create configuration from environment variables only."""
        return cls(
            figma_api_token=os.environ.get("FIGMA_API_TOKEN", ""),
            ai=AIConfig(
                enabled=os.environ.get("AI_ENABLED", "").lower() == "true",
                endpoint=os.environ.get("AI_ENDPOINT_URL", "https://openrouter.ai/api/v1"),
                model=os.environ.get("AI_MODEL", "nvidia/nemotron-3-nano-30b-a3b:free"),
                api_key=os.environ.get("AI_API_KEY", ""),
                temperature=float(os.environ.get("AI_TEMPERATURE", "0.3")),
                max_tokens=int(os.environ.get("AI_MAX_TOKENS", "2000")),
                timeout=int(os.environ.get("AI_TIMEOUT", "60")),
            ),
            output=OutputConfig(
                directory=Path(
                    os.environ.get("OUTPUT_DIRECTORY", os.environ.get("PWD", str(Path.cwd())))
                ),
            ),
        )


def load_config(config_path: Path | None = None) -> FigmaStoriesConfig:
    """Load configuration with fallback to environment variables.

    Args:
        config_path: Optional path to config file. Defaults to
                     config/figma_stories.yaml in project root.

    Returns:
        Validated FigmaStoriesConfig instance.
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "figma_stories.yaml"

    config = FigmaStoriesConfig.load_from_file(config_path)

    if not config.figma_api_token:
        config = FigmaStoriesConfig.from_environment()

    config.validate()
    return config
