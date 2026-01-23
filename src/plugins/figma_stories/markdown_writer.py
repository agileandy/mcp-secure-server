"""Markdown writer for figma-stories-plugin.

This module handles generating markdown output files from user stories
in the specified format.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .config import FigmaStoriesConfig
from .exceptions import OutputError
from .models import Epic, GenerationResult, UserStory


class MarkdownWriter:
    """Write user stories to markdown files."""

    def __init__(self, config: FigmaStoriesConfig):
        """Initialize markdown writer.

        Args:
            config: Plugin configuration
        """
        self.config = config

    def write(
        self,
        result: GenerationResult,
        output_path: Path | None = None,
        interactive: bool = True,
    ) -> Path:
        """Write stories to markdown file.

        Args:
            result: Generation result with epics and stories
            output_path: Optional custom output path
            interactive: Whether to prompt for overwrite/append

        Returns:
            Path to written file

        Raises:
            OutputError: If file write fails
        """
        if not result.success or not result.epics:
            raise OutputError("No stories to write")

        design_title = (
            result.epics[0].stories[0].source_hierarchy[0] if result.epics[0].stories else "Design"
        )

        if output_path is None:
            output_path = self.config.output.get_output_path(design_title)

        output_path = self._resolve_path(output_path)

        if interactive and output_path.exists():
            action = self._prompt_overwrite(output_path)
            if action == "cancel":
                raise OutputError("File write cancelled")
            elif action == "append":
                return self._append_to_file(output_path, result)
            elif action == "rename":
                output_path = self._generate_new_filename(output_path)
                return self._write_to_file(output_path, result)

        return self._write_to_file(output_path, result)

    def _resolve_path(self, path: Path) -> Path:
        """Resolve path against output directory.

        Args:
            path: Input path

        Returns:
            Resolved absolute path
        """
        if path.is_absolute():
            return path
        return self.config.output.directory / path

    def _prompt_overwrite(self, path: Path) -> str:
        """Prompt user for overwrite action.

        Args:
            path: Existing file path

        Returns:
            Action: "overwrite", "append", "rename", or "cancel"
        """
        print(f"\nFile already exists: {path}")
        print("Options:")
        print("  [o]verwrite - Replace the file")
        print("  [a]ppend    - Add to existing file")
        print("  [r]ename    - Generate new filename")
        print("  [c]ancel    - Don't write file")

        while True:
            choice = input("Choose action [o/a/r/c]: ").strip().lower()
            if choice in ("o", "overwrite"):
                return "overwrite"
            elif choice in ("a", "append"):
                return "append"
            elif choice in ("r", "rename"):
                return "rename"
            elif choice in ("c", "cancel"):
                return "cancel"

    def _generate_new_filename(self, path: Path) -> Path:
        """Generate new filename with timestamp.

        Args:
            path: Original path

        Returns:
            New path with timestamp
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = path.stem
        suffix = path.suffix
        new_name = f"{stem}_{timestamp}{suffix}"
        return path.parent / new_name

    def _write_to_file(self, path: Path, result: GenerationResult) -> Path:
        """Write stories to a new file.

        Args:
            path: Output file path
            result: Generation result

        Returns:
            Path to written file
        """
        content = self._generate_content(result)

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            return path
        except PermissionError as e:
            raise OutputError(f"Permission denied writing to {path}: {e}") from e
        except OSError as e:
            raise OutputError(f"Failed to write {path}: {e}") from e

    def _append_to_file(self, path: Path, result: GenerationResult) -> Path:
        """Append stories to existing file.

        Args:
            path: Output file path
            result: Generation result

        Returns:
            Path to modified file
        """
        content = self._generate_content(result, include_header=False)

        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write("\n\n")
                f.write(content)
            return path
        except PermissionError as e:
            raise OutputError(f"Permission denied appending to {path}: {e}") from e
        except OSError as e:
            raise OutputError(f"Failed to append to {path}: {e}") from e

    def _generate_content(
        self,
        result: GenerationResult,
        include_header: bool = True,
        file_url: str = "",
    ) -> str:
        """Generate markdown content.

        Args:
            result: Generation result
            include_header: Whether to include document header
            file_url: Optional Figma file URL

        Returns:
            Markdown content string
        """
        lines = []

        if include_header and result.epics:
            first_epic = result.epics[0]
            if first_epic.stories and first_epic.stories[0].source_hierarchy:
                design_title = first_epic.stories[0].source_hierarchy[0]
            else:
                design_title = "Design"

            lines.append(f"# {design_title} User Story List")
            lines.append("")
            lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            if file_url:
                lines.append(f"**Figma File:** {file_url}")
            lines.append("")
            lines.append("---")
            lines.append("")

        for epic in result.epics:
            if epic.stories:
                lines.extend(self._format_epic(epic))

        return "\n".join(lines)

    def _format_epic(self, epic: Epic) -> list[str]:
        """Format a single epic with its stories.

        Args:
            epic: Epic to format

        Returns:
            List of markdown lines
        """
        lines = []

        lines.append(f"## Epic: {epic.name}")
        lines.append("")

        if epic.description:
            lines.append(epic.description)
            lines.append("")

        for story in epic.stories:
            lines.extend(self._format_story(story))
            lines.append("")

        return lines

    def _format_story(self, story: UserStory) -> list[str]:
        """Format a single user story.

        Args:
            story: UserStory to format

        Returns:
            List of markdown lines
        """
        lines = []

        lines.append(f"### {story.title}")
        lines.append("")

        if story.description:
            lines.append(self._format_description(story.description))
            lines.append("")

        if story.acceptance_criteria:
            lines.append("#### Acceptance Criteria")
            lines.append("")

            for ac in story.acceptance_criteria:
                lines.append(f"Given {ac.given}")
                lines.append(f"When {ac.when_action}")
                lines.append(f"Then {ac.then_outcome}")
                lines.append("")

        if story.component_references:
            lines.append("#### Component References")
            lines.append(", ".join(story.component_references))
            lines.append("")

        if story.source_hierarchy:
            lines.append("#### Source Hierarchy")
            lines.append(" → ".join(story.source_hierarchy))
            lines.append("")

        if story.annotations:
            lines.append("#### Design Notes")
            for annotation in story.annotations[:5]:
                lines.append(f"- {annotation}")
            lines.append("")

        return lines

    def _format_description(self, description: str) -> str:
        """Format user story description with bold formatting.

        Args:
            description: Raw description text

        Returns:
            Formatted description
        """
        if "As a" in description:
            lines = []
            for part in description.split(", "):
                if part.startswith("As a"):
                    lines.append(f"**As a** {part[5:]}")
                elif part.startswith("I want to"):
                    lines.append(f"**I want to** {part[10:]}")
                elif part.startswith("So that"):
                    lines.append(f"**So that** {part[8:]}")
                else:
                    lines.append(part)
            return ", ".join(lines)

        return description

    def preview(self, result: GenerationResult, max_stories: int = 3) -> str:
        """Generate a preview of the markdown content.

        Args:
            result: Generation result
            max_stories: Maximum stories to include per epic

        Returns:
            Preview markdown string
        """
        preview_result = GenerationResult(
            success=result.success,
            epics=[],
            stories_count=result.stories_count,
            components_analyzed=result.components_analyzed,
            ai_enhanced=result.ai_enhanced,
        )

        for epic in result.epics:
            preview_epic = Epic(
                name=epic.name,
                description=epic.description,
                page_data=epic.page_data,
                stories=epic.stories[:max_stories],
            )
            preview_result.epics.append(preview_epic)

        return self._generate_content(preview_result, include_header=True)

    def write_preview(
        self,
        result: GenerationResult,
        preview_path: Path | None = None,
    ) -> Path:
        """Write a preview file.

        Args:
            result: Generation result
            preview_path: Optional custom preview path

        Returns:
            Path to preview file
        """
        if preview_path is None:
            preview_path = self.config.output.directory / "preview.md"

        preview_path = self._resolve_path(preview_path)
        content = self._generate_content(result, include_header=True)

        try:
            preview_path.write_text(content)
            return preview_path
        except OSError as e:
            raise OutputError(f"Failed to write preview: {e}") from e
