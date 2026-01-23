"""Story generation engine for figma-stories-plugin.

This module contains the core logic for generating agile user stories
from Figma design data using templates and optional AI enhancement.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ai_client import AIClientBase
from .config import FigmaStoriesConfig
from .models import (
    AcceptanceCriteria,
    Epic,
    UserStory,
)
from .templates import DefaultAcceptanceCriteria, StoryTemplate


@dataclass
class StoryGenerator:
    """Generate agile user stories from Figma design data."""

    config: FigmaStoriesConfig
    ai_client: AIClientBase | None = None

    def __post_init__(self) -> None:
        """Initialize story template based on configuration."""
        template_format = self.config.story_generation.template_format

        if template_format == "given_when_then":
            self.template = StoryTemplate.given_when_then()
        elif template_format == "user_story_format":
            self.template = StoryTemplate.user_story_format()
        else:
            self.template = StoryTemplate.given_when_then()

    def generate_epics(self, file_data: dict, page_names: list[str] | None = None) -> list[Epic]:
        """Group pages into epics based on configuration.

        Args:
            file_data: Raw file data from Figma API
            page_names: Optional list of page names to include

        Returns:
            List of Epic objects
        """
        epics = []
        pages = file_data.get("pages", [])

        for page in pages:
            if page_names and page.get("name") not in page_names:
                continue

            epic = Epic(
                name=page.get("name", "Untitled"),
                description=f"Stories derived from Figma page: {page.get('name', 'Untitled')}",
                page_data=page,
            )
            epics.append(epic)

        return epics

    def generate_stories(
        self,
        page_data: dict,
        epic: Epic,
        interactive: bool = True,
    ) -> list[UserStory]:
        """Generate user stories from page/frame data.

        Args:
            page_data: Page data from Figma API
            epic: Epic to add stories to
            interactive: Whether to prompt for user input

        Returns:
            List of generated UserStory objects
        """
        stories = []

        if self.config.story_generation.include_components:
            component_stories = self._generate_component_stories(page_data, epic)
            stories.extend(component_stories)

        if self.config.story_generation.include_text_content:
            text_stories = self._generate_text_stories(page_data, epic)
            stories.extend(text_stories)

        epic.stories = stories
        return stories

    def _generate_component_stories(self, page_data: dict, epic: Epic) -> list[UserStory]:
        """Generate stories from components in the design.

        Args:
            page_data: Page data from Figma API
            epic: Epic to add stories to

        Returns:
            List of UserStory objects
        """
        stories = []

        components = self._extract_components_recursive(page_data)

        for component in components:
            story = self._component_to_story(component, epic)
            stories.append(story)

        return stories

    def _extract_components_recursive(
        self, node: dict, parent_hierarchy: list[str] | None = None
    ) -> list[dict]:
        """Recursively extract all components from a node tree.

        Args:
            node: Current node in the tree
            parent_hierarchy: Path from root to this node

        Returns:
            List of component dictionaries with hierarchy
        """
        components = []
        hierarchy = (parent_hierarchy or []) + [node.get("name", "")]

        if node.get("type") in ("COMPONENT", "COMPONENT_SET"):
            component_data = node.copy()
            component_data["_hierarchy"] = hierarchy
            components.append(component_data)

        for child in node.get("children", []):
            components.extend(self._extract_components_recursive(child, hierarchy))

        return components

    def _generate_text_stories(self, page_data: dict, epic: Epic) -> list[UserStory]:
        """Generate stories from text content in the design.

        Args:
            page_data: Page data from Figma API
            epic: Epic to add stories to

        Returns:
            List of UserStory objects
        """
        stories = []

        text_nodes = self._extract_text_nodes_recursive(page_data)

        for text_node in text_nodes:
            story = self._text_to_story(text_node, epic)
            stories.append(story)

        return stories

    def _extract_text_nodes_recursive(
        self, node: dict, parent_hierarchy: list[str] | None = None
    ) -> list[dict]:
        """Recursively extract all text nodes from a node tree.

        Args:
            node: Current node in the tree
            parent_hierarchy: Path from root to this node

        Returns:
            List of text node dictionaries with hierarchy
        """
        text_nodes = []
        hierarchy = (parent_hierarchy or []) + [node.get("name", "")]

        if node.get("type") == "TEXT" and node.get("characters"):
            text_data = node.copy()
            text_data["_hierarchy"] = hierarchy
            text_nodes.append(text_data)

        for child in node.get("children", []):
            text_nodes.extend(self._extract_text_nodes_recursive(child, hierarchy))

        return text_nodes

    def _component_to_story(self, component: dict, epic: Epic) -> UserStory:
        """Convert a component to a user story.

        Args:
            component: Component data from Figma
            epic: Epic this story belongs to

        Returns:
            UserStory object
        """
        name = component.get("name", "Unnamed Component")
        description = component.get("description", "")
        variants = self._extract_variants(component)
        text_content = self._extract_component_text(component)
        hierarchy = component.get("_hierarchy", [])

        title = self._generate_title(name, context=hierarchy)

        if self.ai_client and self.config.is_ai_enabled():
            description = self._sync_ai_description(name, text_content, hierarchy)
        else:
            description = self._template_description(name, text_content)

        acceptance_criteria = self._generate_acceptance_criteria(
            component, text_content, variants, hierarchy
        )

        return UserStory(
            title=title,
            epic=epic.name,
            description=description,
            acceptance_criteria=acceptance_criteria,
            component_references=[name],
            source_hierarchy=hierarchy,
            annotations=self._extract_annotations(component),
        )

    def _text_to_story(self, text_node: dict, epic: Epic) -> UserStory:
        """Convert a text node to a user story.

        Args:
            text_node: Text node data from Figma
            epic: Epic this story belongs to

        Returns:
            UserStory object
        """
        text = text_node.get("characters", "")
        hierarchy = text_node.get("_hierarchy", [])

        title = self._generate_title(text[:30], context=hierarchy)

        if self.ai_client and self.config.is_ai_enabled():
            description = self._sync_ai_description(text, "", hierarchy)
        else:
            description = self._template_description(text, "")

        acceptance_criteria = [
            AcceptanceCriteria(
                given="the text content is displayed",
                when_action="the user views the content",
                then_outcome=f"the text '{text}' shall be visible",
            )
        ]

        return UserStory(
            title=title,
            epic=epic.name,
            description=description,
            acceptance_criteria=acceptance_criteria,
            component_references=[],
            source_hierarchy=hierarchy,
        )

    def _generate_title(self, component_name: str, context: list[str] | None = None) -> str:
        """Generate a story title.

        Args:
            component_name: Name of the component
            context: Hierarchy context

        Returns:
            Title string
        """
        clean_name = self._clean_name(component_name)

        if context and len(context) > 1:
            parent = context[-2] if len(context) > 1 else ""
            if parent and parent.lower() not in clean_name.lower():
                return f"{parent}: {clean_name}"

        return clean_name

    def _clean_name(self, name: str) -> str:
        """Clean a component name for use in a title.

        Args:
            name: Original component name

        Returns:
            Cleaned name
        """
        if not name:
            return "Untitled"

        replacements = [
            ("/primary", ""),
            ("/secondary", ""),
            ("/hover", ""),
            ("/pressed", ""),
            ("/disabled", ""),
            ("-primary", ""),
            ("-secondary", ""),
            ("_primary", ""),
            ("_secondary", ""),
        ]

        result = name
        for old, new in replacements:
            result = result.replace(old, new)

        return result.strip()

    def _template_description(self, component_name: str, text_content: str) -> str:
        """Generate description using template.

        Args:
            component_name: Name of the component
            text_content: Any text content from the component

        Returns:
            Description string
        """
        action = self._infer_action(component_name)

        if text_content:
            benefit = (
                f"I can see '{text_content[:50]}...'"
                if len(text_content) > 50
                else f"I can see '{text_content}'"
            )
        else:
            benefit = "I can interact with this feature"

        return f"As a user, I want to {action}, so that {benefit}"

    async def _ai_generate_description(
        self,
        component_name: str,
        text_content: str,
        context: list[str],
    ) -> str:
        """Generate description using AI.

        Args:
            component_name: Name of the component
            text_content: Any text content from the component
            context: Hierarchy context

        Returns:
            Description string
        """
        if not self.ai_client:
            return self._template_description(component_name, text_content)

        try:
            context_str = " → ".join(context)
            response = await self.ai_client.generate_story_description(
                component_name=component_name,
                context=context_str,
                text_content=text_content[:500] if text_content else "",
            )
            return response
        except Exception:
            return self._template_description(component_name, text_content)

    def _sync_ai_description(
        self,
        component_name: str,
        text_content: str,
        context: list[str],
    ) -> str:
        """Synchronous wrapper for AI description generation."""
        import asyncio

        return asyncio.run(self._ai_generate_description(component_name, text_content, context))

    def _infer_action(self, component_name: str) -> str:
        """Infer user action from component name.

        Args:
            component_name: Name of the component

        Returns:
            Action verb phrase
        """
        name_lower = component_name.lower()

        action_mappings = [
            ("button", "click the button"),
            ("btn", "click the button"),
            ("input", "enter text into the input"),
            ("text field", "enter text into the field"),
            ("checkbox", "toggle the checkbox"),
            ("toggle", "toggle the switch"),
            ("switch", "toggle the switch"),
            ("card", "view the card"),
            ("modal", "interact with the modal"),
            ("dialog", "interact with the dialog"),
            ("menu", "open the menu"),
            ("dropdown", "select from the dropdown"),
            ("select", "make a selection"),
            ("nav", "navigate using the menu"),
            ("link", "follow the link"),
            ("icon", "view the icon"),
            ("avatar", "view the avatar"),
            ("badge", "view the badge"),
            ("alert", "see the alert"),
            ("toast", "see the notification"),
            ("form", "fill out the form"),
            ("search", "perform a search"),
            ("filter", "apply filters"),
            ("sort", "change sort order"),
            ("table", "view the table data"),
            ("list", "view the list"),
            ("grid", "view the grid"),
            ("chart", "view the chart"),
            ("graph", "view the graph"),
            ("progress", "see progress indication"),
            ("loader", "see loading state"),
            ("spinner", "see loading spinner"),
            ("loading", "see loading indicator"),
            ("empty", "see empty state"),
            ("error", "see error state"),
            ("success", "see success confirmation"),
            ("confirm", "confirm an action"),
            ("cancel", "cancel an action"),
            ("close", "close the element"),
            ("back", "go back"),
            ("submit", "submit the form"),
            ("save", "save my changes"),
            ("delete", "delete an item"),
            ("edit", "edit an item"),
            ("add", "add a new item"),
            ("create", "create a new item"),
            ("update", "update an item"),
            ("remove", "remove an item"),
            ("upload", "upload a file"),
            ("download", "download content"),
            ("share", "share content"),
            ("copy", "copy content"),
            ("paste", "paste content"),
            ("expand", "expand the section"),
            ("collapse", "collapse the section"),
            ("scroll", "scroll through content"),
            ("zoom", "zoom in/out"),
            ("pan", "pan the view"),
            ("resize", "resize the element"),
            ("drag", "drag and drop"),
            ("drop", "drop an item"),
            ("swipe", "swipe to navigate"),
            ("pinch", "pinch to zoom"),
            ("rotate", "rotate the item"),
            ("select", "select an item"),
            ("deselect", "deselect an item"),
            ("highlight", "highlight content"),
            ("focus", "focus on the element"),
            ("blur", "remove focus"),
        ]

        for keyword, action in action_mappings:
            if keyword in name_lower:
                return action

        return "interact with this component"

    def _extract_variants(self, component: dict) -> list[str]:
        """Extract variant names from a component.

        Args:
            component: Component data from Figma

        Returns:
            List of variant names
        """
        variants = []
        definitions = component.get("componentPropertyDefinitions", {})

        for prop_name, prop_data in definitions.items():
            if prop_data.get("type") == "VARIANT":
                for option in prop_data.get("variantOptions", []):
                    variants.append(f"{prop_name}: {option}")

        return variants

    def _extract_component_text(self, component: dict) -> str:
        """Extract text content from a component.

        Args:
            component: Component data from Figma

        Returns:
            Combined text content
        """
        texts = []

        def find_text(node: dict) -> None:
            if node.get("type") == "TEXT" and node.get("characters"):
                texts.append(node.get("characters"))
            for child in node.get("children", []):
                find_text(child)

        find_text(component)
        return " ".join(texts)

    def _generate_acceptance_criteria(
        self,
        component: dict,
        text_content: str,
        variants: list[str],
        hierarchy: list[str],
    ) -> list[AcceptanceCriteria]:
        """Generate acceptance criteria for a component.

        Args:
            component: Component data from Figma
            text_content: Any text content from the component
            variants: List of variant names
            hierarchy: Component hierarchy path

        Returns:
            List of AcceptanceCriteria objects
        """
        if self.ai_client and self.config.is_ai_enabled():
            return self._sync_ai_acceptance_criteria(text_content, variants, hierarchy)

        return self._template_acceptance_criteria(component, text_content, variants)

    def _template_acceptance_criteria(
        self,
        component: dict,
        text_content: str,
        variants: list[str],
    ) -> list[AcceptanceCriteria]:
        """Generate acceptance criteria using templates.

        Args:
            component: Component data from Figma
            text_content: Any text content from the component
            variants: List of variant names

        Returns:
            List of AcceptanceCriteria objects
        """
        component_type = self._infer_component_type(component)
        defaults = DefaultAcceptanceCriteria.get_for_type(component_type)

        criteria = []
        for default_ac in defaults:
            criteria.append(
                AcceptanceCriteria(
                    given=default_ac["given"],
                    when_action=default_ac["when"],
                    then_outcome=default_ac["then"],
                )
            )

        if variants:
            for variant in variants[:3]:
                variant_name = variant.split(":")[1].strip() if ":" in variant else variant
                prop_name = variant.split(":")[0].strip() if ":" in variant else "variant"
                criteria.append(
                    AcceptanceCriteria(
                        given=f"the {prop_name} is set to {variant_name}",
                        when_action="the component is rendered",
                        then_outcome=f"the {prop_name.lower()} shall display {variant_name} styling",
                    )
                )

        if text_content:
            display_text = text_content[:50] + "..." if len(text_content) > 50 else text_content
            criteria.append(
                AcceptanceCriteria(
                    given="the component contains text content",
                    when_action="the component is rendered",
                    then_outcome=f"the text '{display_text}' shall be displayed",
                )
            )

        return criteria

    async def _ai_generate_acceptance_criteria(
        self,
        text_content: str,
        variants: list[str],
        hierarchy: list[str],
    ) -> list[AcceptanceCriteria]:
        """Generate acceptance criteria using AI.

        Args:
            text_content: Any text content from the component
            variants: List of variant names
            hierarchy: Component hierarchy path

        Returns:
            List of AcceptanceCriteria objects
        """
        if not self.ai_client:
            return []

        try:
            context_str = " → ".join(hierarchy)
            response = await self.ai_client.generate_acceptance_criteria(
                text_content=text_content[:500] if text_content else "",
                annotations=[],
                variants=variants,
            )

            criteria = []
            for line in response.strip().split("\n\n"):
                if "Given" in line or "When" in line or "Then" in line:
                    parts = self._parse_ai_criteria(line)
                    if parts:
                        criteria.append(AcceptanceCriteria(*parts))

            if not criteria:
                return self._template_acceptance_criteria({}, text_content, variants)

            return criteria

        except Exception:
            return self._template_acceptance_criteria({}, text_content, variants)

    def _sync_ai_acceptance_criteria(
        self,
        text_content: str,
        variants: list[str],
        hierarchy: list[str],
    ) -> list[AcceptanceCriteria]:
        """Synchronous wrapper for AI acceptance criteria generation."""
        import asyncio

        return asyncio.run(self._ai_generate_acceptance_criteria(text_content, variants, hierarchy))

    def _parse_ai_criteria(self, text: str) -> tuple | None:
        """Parse AI-generated acceptance criteria.

        Args:
            text: AI-generated text

        Returns:
            Tuple of (given, when_action, then_outcome) or None if parsing fails
        """
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

    def _infer_component_type(self, component: dict) -> str:
        """Infer component type from node data.

        Args:
            component: Component data from Figma

        Returns:
            Component type string
        """
        name_lower = component.get("name", "").lower()

        type_mappings = [
            ("button", "BUTTON"),
            ("btn", "BUTTON"),
            ("input", "INPUT"),
            ("text field", "INPUT"),
            ("checkbox", "INPUT"),
            ("toggle", "INPUT"),
            ("switch", "INPUT"),
            ("card", "CARD"),
            ("container", "CARD"),
            ("modal", "MODAL"),
            ("dialog", "MODAL"),
            ("popup", "MODAL"),
            ("menu", "NAVIGATION"),
            ("nav", "NAVIGATION"),
            ("navigation", "NAVIGATION"),
            ("sidebar", "NAVIGATION"),
            ("header", "NAVIGATION"),
            ("footer", "NAVIGATION"),
            ("breadcrumb", "NAVIGATION"),
        ]

        for keyword, type_name in type_mappings:
            if keyword in name_lower:
                return type_name

        return "GENERIC"

    def _extract_annotations(self, component: dict) -> list[str]:
        """Extract annotation/comment text from a component.

        Args:
            component: Component data from Figma

        Returns:
            List of annotation strings
        """
        annotations = []

        plugin_data = component.get("pluginData", {})
        shared_data = component.get("sharedPluginData", {})

        for key, value in {**plugin_data, **shared_data}.items():
            if value and isinstance(value, str) and len(value) > 10:
                annotations.append(value[:200])

        return annotations

    def enhance_story(
        self,
        story: UserStory,
        instructions: str = "",
    ) -> UserStory:
        """Enhance an existing story with AI.

        Args:
            story: Original UserStory
            instructions: Optional instructions for enhancement

        Returns:
            Enhanced UserStory
        """
        if not self.ai_client or not self.config.is_ai_enabled():
            return story

        try:
            import asyncio

            enhanced = asyncio.run(
                self.ai_client.enhance_story(
                    story=story,
                    instructions=instructions
                    or "Make the acceptance criteria more specific and testable.",
                )
            )
            return enhanced
        except Exception:
            return story
