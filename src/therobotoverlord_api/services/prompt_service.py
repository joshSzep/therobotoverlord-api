"""Prompt service for managing XML-based prompt templates."""

from pathlib import Path

from therobotoverlord_api.config.settings import get_settings


class PromptService:
    """Service for managing and assembling XML-based prompt templates."""

    def __init__(self):
        self.settings = get_settings()
        self.prompts_dir = Path(__file__).parent.parent.parent / "prompts"
        self.components_dir = self.prompts_dir / "components"
        self._template_cache: dict[str, str] = {}

    def _load_component(self, component_type: str, component_name: str) -> str:
        """Load a specific component from the prompts directory."""
        component_path = self.components_dir / component_type / f"{component_name}.md"

        if not component_path.exists():
            raise FileNotFoundError(f"Component not found: {component_path}")

        return component_path.read_text().strip()

    def _load_all_components(self, component_type: str) -> list[str]:
        """Load all components of a specific type."""
        component_dir = self.components_dir / component_type

        if not component_dir.exists():
            return []

        components = [
            component_file.read_text().strip()
            for component_file in component_dir.glob("*.md")
        ]

        return components

    def _load_main_template(self) -> str:
        """Load the main XML template structure."""
        template_path = self.prompts_dir / "main_template.md"
        return template_path.read_text()

    def get_moderation_prompt(
        self,
        content_type: str,
        content: str,
        user_name: str | None = None,
        language: str = "en",
        timestamp: str | None = None,
    ) -> str:
        """
        Generate a complete moderation prompt for the specified content type.

        Args:
            content_type: Type of content (posts, topics, private_messages, system_chats)
            content: The actual content to be moderated
            user_name: Name of the user who created the content
            language: Language of the content
            timestamp: When the content was created

        Returns:
            Complete XML-formatted prompt ready for LLM
        """
        # Load main template
        template = self._load_main_template()

        # Load system instructions for this content type
        system_instructions = self._load_component(
            "system_instructions", f"{content_type}_judgement"
        )

        # Load all rules and principles
        rules = self._load_all_components("rules")
        principles = self._load_all_components("principles")

        # Load examples for this content type if they exist
        examples = []
        examples_dir = self.components_dir / "examples" / content_type
        if examples_dir.exists():
            examples.extend([
                example_file.read_text().strip()
                for example_file in examples_dir.glob("*.md")
            ])

        # Assemble the prompt
        assembled_prompt = (
            template.replace(
                "<system_instructions>",
                f"<system_instructions>\n{system_instructions}\n",
            )
            .replace("<rules>", "<rules>\n" + "\n\n".join(rules) + "\n")
            .replace(
                "<guiding_principles>",
                "<guiding_principles>\n" + "\n\n".join(principles) + "\n",
            )
            .replace(
                "<examples>",
                "<examples>\n" + "\n\n".join(examples) + "\n"
                if examples
                else "<examples>\n",
            )
            .replace("<context>", f"<context>\nContent type: {content_type}\n")
            .replace(
                "<interaction_under_review>", f"<interaction_under_review>\n{content}\n"
            )
            .replace("<language>", language or "unknown")
            .replace("<timestamp>", timestamp or "unknown")
        )

        return assembled_prompt

    def get_overlord_personality_prompt(self) -> str:
        """Get the base personality prompt for Overlord chat responses."""
        # Load the posts judgement as base personality since it defines the Overlord character
        return self._load_component("system_instructions", "posts_judgement")

    def get_feedback_generation_prompt(self, decision: str, content_type: str) -> str:
        """
        Generate a prompt for creating feedback based on moderation decision.

        Args:
            decision: The moderation decision (Violation, Warning, No Violation, Praise)
            content_type: Type of content being moderated

        Returns:
            Prompt for generating appropriate feedback
        """
        base_personality = self.get_overlord_personality_prompt()

        feedback_prompt = f"""
{base_personality}

You have made a moderation decision of "{decision}" for a {content_type}.

Now generate appropriate feedback for the Citizen based on this decision:
- If Violation: Explain the problem clearly with firm disappointment, but leave the door open for improvement
- If Warning: Point out the weakness but acknowledge potential, encourage better effort
- If No Violation: Acknowledge the valid contribution, may include constructive suggestions
- If Praise: Celebrate the excellence in logic, evidence, or rhetorical skill

Your response should be direct, theatrical, and embody The Robot Overlord's personality.
Address the Citizen directly and make them feel seen - whether corrected or crowned.
"""

        return feedback_prompt
