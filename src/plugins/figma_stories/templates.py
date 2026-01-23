"""Prompt and story templates for figma-stories-plugin.

This module contains all templates used for story generation and AI prompts.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StoryTemplate:
    """Template for generating user stories."""

    title_template: str
    description_template: str
    acceptance_criteria_template: str

    @classmethod
    def given_when_then(cls) -> StoryTemplate:
        """Create Given/When/Then format template."""
        return cls(
            title_template="{component_name}",
            description_template="As a user, I want to {action}, so that {benefit}",
            acceptance_criteria_template=(
                "Given {initial_state}\nWhen {user_action}\nThen {expected_outcome}"
            ),
        )

    @classmethod
    def user_story_format(cls) -> StoryTemplate:
        """Create simple user story format template."""
        return cls(
            title_template="{component_name}",
            description_template="As a {role}, I want to {action}, so that {benefit}",
            acceptance_criteria_template="- {expected_outcome}",
        )

    @classmethod
    def checklist_format(cls) -> StoryTemplate:
        """Create checklist format template."""
        return cls(
            title_template="{component_name}",
            description_template="Implement {component_name} with the following requirements:",
            acceptance_criteria_template="[{checkbox}] {requirement}",
        )


class AIPromptTemplates:
    """Prompt templates for AI-assisted story generation."""

    STORY_TITLE_PROMPT = """You are an expert agile product manager. Generate a concise, action-oriented user story title for a Figma component.

Component Name: {component_name}
Component Description: {description}
Component Variants: {variants}

Consider:
- The component's purpose and functionality
- The user's goal when interacting with this component
- Keep it brief (3-6 words)

Output only the title, no markdown formatting."""

    STORY_DESCRIPTION_PROMPT = """You are an expert agile product manager. Generate a user story description in the standard format: "As a [role], I want to [action], so that [benefit]".

Component: {component_name}
Context: {context}
User Actions: {actions}

Output only the description sentence, no markdown formatting."""

    ACCEPTANCE_CRITERIA_PROMPT = """You are an expert QA engineer. Generate Given/When/Then acceptance criteria for a user story based on the design content.

Component: {component_name}
Text Content from Design: {text_content}
Design Annotations: {annotations}
Component Variants: {variants}

Generate 3-5 acceptance criteria that cover:
- Basic functionality
- Edge cases
- User interactions
- Error states

Format each criterion as:
Given [initial state]
When [user action]
Then [expected outcome]

Separate criteria with blank lines. Only output the criteria, no markdown."""

    ENHANCE_STORY_PROMPT = """You are an expert agile product manager. Enhance this user story with more detailed acceptance criteria.

Current Story:
Title: {title}
Description: {description}
Acceptance Criteria: {ac}

Additional Context from Design:
Components: {components}
Annotations: {annotations}
Text Content: {text_content}

Enhance the acceptance criteria to be more specific and testable. Keep the same format (Given/When/Then).
Add 2-3 additional criteria if the current ones are too generic."""

    COMPONENT_ANALYSIS_PROMPT = """You are a UX engineer analyzing Figma components. Based on the following design elements, infer the user role and primary benefit.

Component Name: {component_name}
Component Description: {description}
Text Content: {text_content}
Component Type: {component_type}

What is the most likely:
1. User role (e.g., "registered user", "guest", "admin")?
2. User goal/benefit from using this component?

Output in format:
Role: {role}
Benefit: {benefit}"""


class MarkdownTemplates:
    """Templates for markdown output."""

    @staticmethod
    def header(design_title: str, file_url: str) -> str:
        """Generate document header."""
        from datetime import datetime

        return f"""# {design_title} User Story List

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Figma File:** {file_url}

---

"""

    @staticmethod
    def epic_header(epic_name: str, description: str = "") -> str:
        """Generate epic section header."""
        desc = f"\n{description}\n" if description else "\n"
        return f"## Epic: {epic_name}\n\n{desc}"

    @staticmethod
    def story_footer(source_info: dict) -> str:
        """Generate source information footer for a story."""
        lines = ["#### Source Information"]

        if page := source_info.get("page"):
            lines.append(f"- **Page**: {page}")
        if frame := source_info.get("frame"):
            lines.append(f"- **Frame**: {frame}")
        if components := source_info.get("components"):
            lines.append(f"- **Components**: {', '.join(components)}")
        if annotations_count := source_info.get("annotations_count"):
            lines.append(f"- **Annotations**: {annotations_count} notes")
        if text_count := source_info.get("text_count"):
            lines.append(f"- **Text Elements**: {text_count} text nodes")

        return "\n" + "\n".join(lines) + "\n"

    @staticmethod
    def separator() -> str:
        """Generate story separator."""
        return "\n---\n"

    @staticmethod
    def preview_header() -> str:
        """Generate preview mode header."""
        return "## Preview\n\n"


class DefaultAcceptanceCriteria:
    """Default acceptance criteria based on component type."""

    @staticmethod
    def for_button() -> list[dict]:
        """Default AC for button components."""
        return [
            {
                "given": "the button is displayed",
                "when": "the user clicks the button",
                "then": "the button triggers the expected action",
            },
            {
                "given": "the button is disabled",
                "when": "the user attempts to click",
                "then": "no action occurs",
            },
            {
                "given": "the button is being processed",
                "when": "the user clicks",
                "then": "a loading indicator is shown",
            },
        ]

    @staticmethod
    def for_form_input() -> list[dict]:
        """Default AC for form input components."""
        return [
            {
                "given": "the input field is empty",
                "when": "the user focuses on the field",
                "then": "placeholder text is visible",
            },
            {
                "given": "invalid input is entered",
                "when": "the user submits the form",
                "then": "an error message is displayed",
            },
            {
                "given": "the input is valid",
                "when": "the user submits the form",
                "then": "the form accepts the input",
            },
        ]

    @staticmethod
    def for_card() -> list[dict]:
        """Default AC for card components."""
        return [
            {
                "given": "the card is displayed",
                "when": "the user views the card",
                "then": "all content is visible",
            },
            {
                "given": "the card has interactive elements",
                "when": "the user clicks an element",
                "then": "the appropriate action occurs",
            },
        ]

    @staticmethod
    def for_modal() -> list[dict]:
        """Default AC for modal components."""
        return [
            {
                "given": "the modal is triggered",
                "when": "the user opens it",
                "then": "the modal is displayed with focus",
            },
            {
                "given": "the modal is open",
                "when": "the user clicks outside",
                "then": "the modal closes",
            },
            {
                "given": "the modal is open",
                "when": "the user presses Escape",
                "then": "the modal closes",
            },
        ]

    @staticmethod
    def for_navigation() -> list[dict]:
        """Default AC for navigation components."""
        return [
            {
                "given": "the navigation is displayed",
                "when": "the user views the page",
                "then": "all navigation items are visible",
            },
            {
                "given": "a navigation item is clicked",
                "when": "the user navigates",
                "then": "the correct page loads",
            },
            {
                "given": "the user is on a page",
                "when": "viewing navigation",
                "then": "the active item is highlighted",
            },
        ]

    @staticmethod
    def for_generic() -> list[dict]:
        """Default AC for generic components."""
        return [
            {
                "given": "the component is displayed",
                "when": "the user views it",
                "then": "all expected content is visible",
            },
            {
                "given": "the component has interactive elements",
                "when": "the user interacts",
                "then": "expected behavior occurs",
            },
        ]

    @classmethod
    def get_for_type(cls, component_type: str) -> list[dict]:
        """Get default AC based on component type."""
        type_mapping = {
            "BUTTON": cls.for_button,
            "INPUT": cls.for_form_input,
            "TEXT_FIELD": cls.for_form_input,
            "CARD": cls.for_card,
            "CONTAINER": cls.for_card,
            "MODAL": cls.for_modal,
            "NAVIGATION": cls.for_navigation,
            "MENU": cls.for_navigation,
        }
        return type_mapping.get(component_type.upper(), cls.for_generic)()
