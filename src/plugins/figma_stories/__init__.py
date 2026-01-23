"""Figma Stories MCP Plugin.

This module provides MCP tools for generating agile user stories from Figma designs.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from ..base import PluginBase, ToolDefinition, ToolResult
from .ai_client import AIClientBase, create_ai_client
from .config import FigmaStoriesConfig, load_config
from .exceptions import (
    ConfigurationError,
    FigmaAPIError,
    FigmaAuthenticationError,
    FigmaFileNotFoundError,
    FigmaRateLimitError,
    GenerationError,
    OutputError,
)
from .figma_client import FigmaClient
from .markdown_writer import MarkdownWriter
from .models import GenerationResult
from .story_generator import StoryGenerator


@dataclass
class FigmaStoriesPlugin(PluginBase):
    """MCP Plugin for generating agile user stories from Figma designs."""

    def __init__(self, config: FigmaStoriesConfig | None = None):
        """Initialize plugin.

        Args:
            config: Optional pre-loaded configuration
        """
        self._config = config
        self._figma_client: FigmaClient | None = None
        self._ai_client: AIClientBase | None = None

    @property
    def name(self) -> str:
        return "figma_stories"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def category(self) -> str:
        return "agile"

    def _get_config(self) -> FigmaStoriesConfig:
        """Get configuration, loading if necessary."""
        if self._config is None:
            self._config = load_config()
        return self._config

    def _get_figma_client(self) -> FigmaClient:
        """Get or create Figma client."""
        if self._figma_client is None:
            config = self._get_config()
            self._figma_client = FigmaClient(
                api_token=config.figma_api_token,
                timeout=30,
            )
        return self._figma_client

    def _get_ai_client(self) -> AIClientBase:
        """Get or create AI client."""
        if self._ai_client is None:
            config = self._get_config()
            client = create_ai_client(config)
            if client is None:
                raise ConfigurationError("Failed to create AI client")
            self._ai_client = client
        return self._ai_client

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="configure_figma_stories",
                description="Configure Figma Stories plugin with API tokens and AI settings. "
                "Set FIGMA_API_TOKEN environment variable for Figma access.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "figma_token": {
                            "type": "string",
                            "description": "Figma API token (alternative: set FIGMA_API_TOKEN env var)",
                        },
                        "ai_enabled": {
                            "type": "boolean",
                            "description": "Enable AI enhancement for story generation",
                            "default": False,
                        },
                        "ai_endpoint": {
                            "type": "string",
                            "description": "AI API endpoint URL",
                            "default": "https://openrouter.ai/api/v1",
                        },
                        "ai_model": {
                            "type": "string",
                            "description": "AI model name",
                            "default": "nvidia/nemotron-3-nano-30b-a3b:free",
                        },
                        "ai_api_key": {
                            "type": "string",
                            "description": "AI API key (alternative: set AI_API_KEY env var)",
                        },
                    },
                },
            ),
            ToolDefinition(
                name="generate_user_stories",
                description="Generate agile user stories from a Figma design file. "
                "Creates markdown file with stories, epics, and acceptance criteria.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_url": {
                            "type": "string",
                            "description": "Figma file URL (e.g., https://www.figma.com/file/abc123/...)",
                        },
                        "pages": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific pages to process (empty = all pages)",
                        },
                        "output_file": {
                            "type": "string",
                            "description": "Output filename (default: {design_title}_user_stories.md)",
                        },
                        "interactive": {
                            "type": "boolean",
                            "description": "Prompt for overwrite/append if file exists",
                            "default": True,
                        },
                    },
                    "required": ["file_url"],
                },
            ),
            ToolDefinition(
                name="preview_user_stories",
                description="Preview generated user stories without writing to file. "
                "Shows first 3 stories per epic.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_url": {
                            "type": "string",
                            "description": "Figma file URL",
                        },
                        "pages": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific pages to preview",
                        },
                    },
                    "required": ["file_url"],
                },
            ),
            ToolDefinition(
                name="list_figma_pages",
                description="List pages in a Figma file for selection.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_url": {
                            "type": "string",
                            "description": "Figma file URL",
                        },
                    },
                    "required": ["file_url"],
                },
            ),
            ToolDefinition(
                name="get_config_status",
                description="Get current configuration status.",
                input_schema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute a tool.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            ToolResult with content or error
        """
        try:
            if tool_name == "configure_figma_stories":
                return self._configure(arguments)
            elif tool_name == "generate_user_stories":
                return self._generate_stories(arguments)
            elif tool_name == "preview_user_stories":
                return self._preview_stories(arguments)
            elif tool_name == "list_figma_pages":
                return self._list_pages(arguments)
            elif tool_name == "get_config_status":
                return self._get_config_status(arguments)
            else:
                return ToolResult(
                    content=[{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                    is_error=True,
                )
        except FigmaAuthenticationError as e:
            return ToolResult(
                content=[{"type": "text", "text": f"Figma authentication failed: {e.message}"}],
                is_error=True,
            )
        except FigmaFileNotFoundError as e:
            return ToolResult(
                content=[{"type": "text", "text": f"Figma file not found: {e.message}"}],
                is_error=True,
            )
        except FigmaRateLimitError as e:
            return ToolResult(
                content=[
                    {
                        "type": "text",
                        "text": f"Figma API rate limit exceeded. Retry after {e.retry_after}s",
                    }
                ],
                is_error=True,
            )
        except FigmaAPIError as e:
            return ToolResult(
                content=[{"type": "text", "text": f"Figma API error: {e.message}"}],
                is_error=True,
            )
        except ConfigurationError as e:
            return ToolResult(
                content=[{"type": "text", "text": f"Configuration error: {e.message}"}],
                is_error=True,
            )
        except OutputError as e:
            return ToolResult(
                content=[{"type": "text", "text": f"Output error: {e.message}"}],
                is_error=True,
            )
        except GenerationError as e:
            return ToolResult(
                content=[{"type": "text", "text": f"Story generation error: {e.message}"}],
                is_error=True,
            )
        except Exception as e:
            return ToolResult(
                content=[{"type": "text", "text": f"Unexpected error: {str(e)}"}],
                is_error=True,
            )

    def _configure(self, arguments: dict) -> ToolResult:
        """Configure the plugin."""
        config = self._get_config()

        if figma_token := arguments.get("figma_token"):
            config.figma_api_token = figma_token

        if "ai_enabled" in arguments:
            config.ai.enabled = arguments["ai_enabled"]

        if ai_endpoint := arguments.get("ai_endpoint"):
            config.ai.endpoint = ai_endpoint

        if ai_model := arguments.get("ai_model"):
            config.ai.model = ai_model

        if ai_api_key := arguments.get("ai_api_key"):
            config.ai.api_key = ai_api_key

        config.validate()

        return ToolResult(
            content=[
                {
                    "type": "text",
                    "text": f"""Figma Stories Plugin Configuration:

- Figma API Token: {"✓ Set" if config.figma_api_token else "✗ Not set"}
- AI Enabled: {"✓ Yes" if config.is_ai_enabled() else "✗ No"}
- AI Provider: {config.ai.provider}
- AI Model: {config.ai.model}
- Output Directory: {config.output.directory}

To use AI features, set AI_API_KEY environment variable or provide it via the tool.""",
                }
            ],
            is_error=False,
        )

    def _generate_stories(self, arguments: dict) -> ToolResult:
        """Generate user stories from Figma file."""
        config = self._get_config()

        file_url = arguments["file_url"]
        pages = arguments.get("pages", [])
        output_file = arguments.get("output_file")
        interactive = arguments.get("interactive", True)

        figma_client = self._get_figma_client()
        ai_client = self._get_ai_client()

        file_key = figma_client.extract_file_key(file_url)

        async def generate() -> GenerationResult:
            async with figma_client:
                design_data = await figma_client.get_full_design_data(
                    file_key, pages if pages else None
                )

                generator = StoryGenerator(config=config, ai_client=ai_client)
                epics = generator.generate_epics(design_data, pages if pages else None)

                for epic in epics:
                    generator.generate_stories(epic.page_data, epic, interactive=interactive)

                result = GenerationResult(
                    success=True,
                    epics=epics,
                    stories_count=sum(len(e.stories) for e in epics),
                    components_analyzed=len(design_data.get("components", [])),
                    ai_enhanced=config.is_ai_enabled(),
                )

                if output_file or interactive:
                    output_path = Path(output_file) if output_file else None
                    writer = MarkdownWriter(config)
                    file_path = writer.write(result, output_path, interactive=interactive)
                    result.file_written = file_path

                return result

        result = asyncio.run(generate())

        content = [
            {
                "type": "text",
                "text": f"Generated {result.stories_count} stories from {len(result.epics)} epics.",
            }
        ]

        if result.file_written:
            content[0]["text"] += f"\nOutput written to: {result.file_written}"

        return ToolResult(content=content, is_error=False)

    def _preview_stories(self, arguments: dict) -> ToolResult:
        """Preview user stories without writing to file."""
        config = self._get_config()

        file_url = arguments["file_url"]
        pages = arguments.get("pages", [])

        figma_client = self._get_figma_client()
        ai_client = self._get_ai_client()

        file_key = figma_client.extract_file_key(file_url)

        async def preview() -> GenerationResult:
            async with figma_client:
                design_data = await figma_client.get_full_design_data(
                    file_key, pages if pages else None
                )

                generator = StoryGenerator(config=config, ai_client=ai_client)
                epics = generator.generate_epics(design_data, pages if pages else None)

                for epic in epics:
                    generator.generate_stories(epic.page_data, epic, interactive=False)

                return GenerationResult(
                    success=True,
                    epics=epics,
                    stories_count=sum(len(e.stories) for e in epics),
                    components_analyzed=len(design_data.get("components", [])),
                    ai_enhanced=config.is_ai_enabled(),
                )

        result = asyncio.run(preview())
        writer = MarkdownWriter(config)
        preview_content = writer.preview(result)

        return ToolResult(
            content=[{"type": "text", "text": preview_content}],
            is_error=False,
        )

    def _list_pages(self, arguments: dict) -> ToolResult:
        """List pages in a Figma file."""
        file_url = arguments["file_url"]

        figma_client = self._get_figma_client()
        file_key = figma_client.extract_file_key(file_url)

        async def list_pages():
            async with figma_client:
                file_info = await figma_client.get_file_info(file_key)
                return file_info

        file_info = asyncio.run(list_pages())

        pages_text = "\n".join(f"- {page.name}" for page in file_info.pages)

        return ToolResult(
            content=[
                {
                    "type": "text",
                    "text": f"Figma File: {file_info.name}\n\nPages:\n{pages_text}",
                }
            ],
            is_error=False,
        )

    def _get_config_status(self, arguments: dict) -> ToolResult:
        """Get configuration status."""
        config = self._get_config()

        return ToolResult(
            content=[
                {
                    "type": "text",
                    "text": f"""Figma Stories Plugin Status:

Configuration:
- Figma API Token: {"✓ Set" if config.figma_api_token else "✗ Not set (set FIGMA_API_TOKEN env var)"}
- AI Enabled: {"✓ Yes" if config.is_ai_enabled() else "✗ No"}
- AI Provider: {config.ai.provider}
- AI Model: {config.ai.model}
- AI Endpoint: {config.ai.endpoint}
- Output Directory: {config.output.directory}

To enable AI:
1. Set AI_API_KEY environment variable, or
2. Provide ai_api_key via configure_figma_stories tool

To set Figma token:
1. Set FIGMA_API_TOKEN environment variable, or
2. Provide figma_token via configure_figma_stories tool""",
                }
            ],
            is_error=False,
        )

    def cleanup(self) -> None:
        """Clean up plugin resources."""
        if self._figma_client:
            asyncio.run(self._figma_client.close())
        self._figma_client = None
        self._ai_client = None
