"""Data models for figma-stories-plugin.

This module defines the core data structures used throughout the plugin,
including user stories, acceptance criteria, and Figma API response models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class StoryTemplateFormat(Enum):
    """Story template format options."""

    GIVEN_WHEN_THEN = "given_when_then"
    USER_STORY_FORMAT = "user_story_format"
    CHECKLIST = "checklist"


class EpicSource(Enum):
    """Source for epic identification."""

    PAGE_NAME = "page_name"
    FRAME_NAME = "frame_name"
    USER_INPUT = "user_input"


class AIProvider(Enum):
    """Supported AI providers."""

    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    CUSTOM = "custom"


@dataclass
class AcceptanceCriteria:
    """Single acceptance criterion in Given/When/Then format."""

    given: str
    when_action: str
    then_outcome: str

    def to_markdown(self) -> str:
        """Convert to markdown format."""
        return f"Given {self.given}\nWhen {self.when_action}\nThen {self.then_outcome}"

    @classmethod
    def from_text(cls, text: str) -> AcceptanceCriteria:
        """Parse from structured text format."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if len(lines) >= 3 and all(
            line.lower().startswith(prefix)
            for line, prefix in zip(lines[:3], ["given", "when", "then"], strict=False)
        ):
            return cls(
                given=lines[0][6:].strip(),
                when_action=lines[1][5:].strip(),
                then_outcome=lines[2][5:].strip(),
            )
        raise ValueError(f"Cannot parse acceptance criteria from: {text}")


@dataclass
class UserStory:
    """User story with acceptance criteria."""

    title: str
    epic: str
    description: str
    acceptance_criteria: list[AcceptanceCriteria] = field(default_factory=list)
    component_references: list[str] = field(default_factory=list)
    source_hierarchy: list[str] = field(default_factory=list)
    annotations: list[str] = field(default_factory=list)
    technical_notes: str | None = None

    def to_markdown(self) -> str:
        """Convert to markdown format."""
        lines = [
            f"### {self.title}",
            "",
            f"**As a** {self._extract_role()}",
            f"**I want to** {self._extract_action()}",
            f"**So that** {self._extract_benefit()}",
            "",
            "#### Acceptance Criteria",
            "",
        ]

        for ac in self.acceptance_criteria:
            lines.append(ac.to_markdown())
            lines.append("")

        if self.component_references:
            lines.append("#### Component References")
            lines.append(", ".join(self.component_references))
            lines.append("")

        if self.source_hierarchy:
            lines.append("#### Source Hierarchy")
            lines.append(" → ".join(self.source_hierarchy))
            lines.append("")

        return "\n".join(lines)

    def _extract_role(self) -> str:
        """Extract user role from description."""
        if "As a" in self.description:
            parts = self.description.split("As a")
            if len(parts) > 1:
                role_part = parts[1].split(",")[0].strip()
                return role_part
        return "user"

    def _extract_action(self) -> str:
        """Extract user action from description."""
        if "I want to" in self.description:
            parts = self.description.split("I want to")
            if len(parts) > 1:
                action_part = parts[1].split(",")[0].strip()
                return action_part
        return "interact with this feature"

    def _extract_benefit(self) -> str:
        """Extract benefit from description."""
        if "So that" in self.description:
            parts = self.description.split("So that")
            if len(parts) > 1:
                return parts[1].strip()
        return "I can achieve my goals"


@dataclass
class Epic:
    """Epic containing related user stories."""

    name: str
    description: str
    page_data: dict = field(default_factory=dict)
    stories: list[UserStory] = field(default_factory=list)


@dataclass
class Page:
    """Figma page extracted from file."""

    id: str
    name: str
    node_id: str
    children: list[dict] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> Page:
        """Create from Figma API response."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", "Untitled"),
            node_id=data.get("nodeId", ""),
            children=data.get("children", []),
        )


@dataclass
class Component:
    """Figma component extracted from design."""

    id: str
    name: str
    description: str
    node_id: str
    properties: dict = field(default_factory=dict)
    variants: list[str] = field(default_factory=list)
    usage_count: int = 0
    parent_frame: str = ""

    @classmethod
    def from_dict(cls, data: dict, parent_frame: str = "") -> Component:
        """Create from Figma API component data."""
        definitions = data.get("componentPropertyDefinitions", {})
        variants = [
            opt
            for prop in definitions.values()
            if prop.get("type") == "VARIANT"
            for opt in prop.get("variantOptions", [])
        ]

        return cls(
            id=data.get("id", ""),
            name=data.get("name", "Unnamed Component"),
            description=data.get("description", ""),
            node_id=data.get("nodeId", ""),
            properties=definitions,
            variants=variants,
            usage_count=0,
            parent_frame=parent_frame,
        )


@dataclass
class TextNode:
    """Text node extracted from design."""

    id: str
    characters: str
    style: dict = field(default_factory=dict)
    hierarchy: list[str] = field(default_factory=list)
    parent_component: str | None = None

    @classmethod
    def from_dict(cls, data: dict, hierarchy: list[str] | None = None) -> TextNode:
        """Create from Figma API text node data."""
        return cls(
            id=data.get("id", ""),
            characters=data.get("characters", ""),
            style=data.get("style", {}),
            hierarchy=hierarchy or [],
            parent_component=data.get("componentId") or None,
        )


@dataclass
class Frame:
    """Frame extracted from design."""

    id: str
    name: str
    node_id: str
    children_count: int = 0
    component_references: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> Frame:
        """Create from Figma API frame data."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", "Unnamed Frame"),
            node_id=data.get("nodeId", ""),
            children_count=len(data.get("children", [])),
            component_references=[],
        )


@dataclass
class Annotation:
    """Design annotation or comment."""

    id: str
    content: str
    author: str | None = None
    created_at: datetime | None = None
    node_ids: list[str] = field(default_factory=list)

    @classmethod
    def from_comment(cls, data: dict) -> Annotation:
        """Create from Figma comment data."""
        return cls(
            id=data.get("id", ""),
            content=data.get("message", ""),
            author=data.get("user", {}).get("handle"),
            created_at=datetime.fromisoformat(data.get("created_at", "").replace("Z", "+00:00"))
            if data.get("created_at")
            else None,
            node_ids=[data.get("client_meta", {}).get("node_id", "")],
        )


@dataclass
class FileInfo:
    """Figma file metadata."""

    key: str
    name: str
    last_modified: datetime
    thumbnail_url: str | None = None
    version: str = ""
    pages: list[Page] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> FileInfo:
        """Create from Figma API file response."""
        return cls(
            key=data.get("key", ""),
            name=data.get("name", "Untitled"),
            last_modified=datetime.fromisoformat(
                data.get("lastModified", "").replace("Z", "+00:00")
            )
            if data.get("lastModified")
            else datetime.now(),
            thumbnail_url=data.get("thumbnailUrl"),
            version=data.get("version", ""),
            pages=[Page.from_dict(page) for page in data.get("document", {}).get("children", [])],
        )


@dataclass
class GenerationResult:
    """Result of story generation operation."""

    success: bool
    epics: list[Epic] = field(default_factory=list)
    file_written: Path | None = None
    stories_count: int = 0
    components_analyzed: int = 0
    ai_enhanced: bool = False
    error_message: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for MCP response."""
        result = {
            "status": "success" if self.success else "error",
            "epics_count": len(self.epics),
            "stories_count": self.stories_count,
            "components_analyzed": self.components_analyzed,
            "ai_enhanced": self.ai_enhanced,
        }

        if self.file_written:
            result["file_written"] = str(self.file_written)

        if self.success and self.epics:
            if self.epics[0].stories:
                result["preview"] = self.epics[0].stories[0].to_markdown()[:500]

        if not self.success and self.error_message:
            result["error"] = self.error_message

        return result
