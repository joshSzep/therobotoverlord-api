"""Tag service for The Robot Overlord API."""

from uuid import UUID

from therobotoverlord_api.database.models.tag import Tag
from therobotoverlord_api.database.models.tag import TagCreate
from therobotoverlord_api.database.models.tag import TagUpdate
from therobotoverlord_api.database.models.tag import TagWithTopicCount
from therobotoverlord_api.database.models.tag import TopicTag
from therobotoverlord_api.database.models.tag import TopicTagCreate
from therobotoverlord_api.database.models.tag import TopicTagWithDetails
from therobotoverlord_api.database.repositories.tag import TagRepository
from therobotoverlord_api.database.repositories.tag import TopicTagRepository
from therobotoverlord_api.database.repositories.topic import TopicRepository


class TagService:
    """Service for tag-related business logic."""

    def __init__(self):
        self.tag_repo = TagRepository()
        self.topic_tag_repo = TopicTagRepository()
        self.topic_repo = TopicRepository()

    async def create_tag(self, tag_data: TagCreate) -> Tag:
        """Create a new tag."""
        # Check if tag with same name already exists
        existing_tag = await self.tag_repo.get_by_name(tag_data.name)
        if existing_tag:
            raise ValueError(f"Tag with name '{tag_data.name}' already exists")

        return await self.tag_repo.create(tag_data)

    async def update_tag(self, tag_pk: UUID, tag_data: TagUpdate) -> Tag:
        """Update an existing tag."""
        # Check if tag exists
        existing_tag = await self.tag_repo.get_by_pk(tag_pk)
        if not existing_tag:
            raise ValueError(f"Tag with PK {tag_pk} not found")

        # If updating name, check for conflicts
        if tag_data.name and tag_data.name != existing_tag.name:
            name_conflict = await self.tag_repo.get_by_name(tag_data.name)
            if name_conflict:
                raise ValueError(f"Tag with name '{tag_data.name}' already exists")

        updated_tag = await self.tag_repo.update(tag_pk, tag_data)
        if not updated_tag:
            raise ValueError(f"Failed to update tag with PK {tag_pk}")

        return updated_tag

    async def delete_tag(self, tag_pk: UUID) -> bool:
        """Delete a tag and all its topic assignments."""
        # Check if tag exists
        existing_tag = await self.tag_repo.get_by_pk(tag_pk)
        if not existing_tag:
            raise ValueError(f"Tag with PK {tag_pk} not found")

        # Note: topic_tags will be deleted automatically due to CASCADE constraint
        return await self.tag_repo.delete_by_pk(tag_pk)

    async def get_tag_by_pk(self, tag_pk: UUID) -> Tag | None:
        """Get tag by primary key."""
        return await self.tag_repo.get_by_pk(tag_pk)

    async def get_tag_by_name(self, name: str) -> Tag | None:
        """Get tag by name."""
        return await self.tag_repo.get_by_name(name)

    async def get_all_tags(self, limit: int = 100, offset: int = 0) -> list[Tag]:
        """Get all tags with pagination."""
        return await self.tag_repo.get_all(limit=limit, offset=offset)

    async def search_tags(
        self, search_term: str, limit: int = 50, offset: int = 0
    ) -> list[Tag]:
        """Search tags by name."""
        return await self.tag_repo.search_tags(search_term, limit=limit, offset=offset)

    async def get_tags_with_topic_count(
        self, limit: int = 100, offset: int = 0
    ) -> list[TagWithTopicCount]:
        """Get tags with their topic counts."""
        return await self.tag_repo.get_tags_with_topic_count(limit=limit, offset=offset)

    async def get_popular_tags(self, limit: int = 20) -> list[TagWithTopicCount]:
        """Get most popular tags by topic count."""
        return await self.tag_repo.get_popular_tags(limit=limit)

    async def assign_tag_to_topic(
        self, topic_pk: UUID, tag_pk: UUID, assigned_by_pk: UUID
    ) -> TopicTag:
        """Assign a tag to a topic."""
        # Verify topic exists
        topic = await self.topic_repo.get_by_pk(topic_pk)
        if not topic:
            raise ValueError(f"Topic with PK {topic_pk} not found")

        # Verify tag exists
        tag = await self.tag_repo.get_by_pk(tag_pk)
        if not tag:
            raise ValueError(f"Tag with PK {tag_pk} not found")

        # Check if tag is already assigned to topic
        if await self.topic_tag_repo.tag_exists_for_topic(topic_pk, tag_pk):
            raise ValueError(f"Tag '{tag.name}' is already assigned to this topic")

        topic_tag_data = TopicTagCreate(topic_pk=topic_pk, tag_pk=tag_pk)

        return await self.topic_tag_repo.create(topic_tag_data)

    async def assign_tags_to_topic(
        self,
        topic_pk: UUID,
        tag_names: list[str],
    ) -> list[TopicTag]:
        """Assign multiple tags to a topic by name."""
        # Verify topic exists
        topic = await self.topic_repo.get_by_pk(topic_pk)
        if not topic:
            raise ValueError(f"Topic with PK {topic_pk} not found")

        assigned_tags: list[TopicTag] = []

        for tag_name in tag_names:
            # Get or create tag
            tag = await self.tag_repo.get_by_name(tag_name)
            if not tag:
                # Auto-create tag if it doesn't exist (Overlord can create new tags)
                tag_data = TagCreate(
                    name=tag_name, description=f"Auto-created tag for '{tag_name}'"
                )
                tag = await self.tag_repo.create(tag_data)

            # Skip if tag is already assigned
            if await self.topic_tag_repo.tag_exists_for_topic(topic_pk, tag.pk):
                continue

            # Assign tag to topic
            topic_tag_data = TopicTagCreate(topic_pk=topic_pk, tag_pk=tag.pk)

            assigned_tag = await self.topic_tag_repo.create(topic_tag_data)
            assigned_tags.append(assigned_tag)

        return assigned_tags

    async def remove_tag_from_topic(self, topic_pk: UUID, tag_pk: UUID) -> bool:
        """Remove a tag from a topic."""
        # Verify topic exists
        topic = await self.topic_repo.get_by_pk(topic_pk)
        if not topic:
            raise ValueError(f"Topic with PK {topic_pk} not found")

        # Verify tag exists
        tag = await self.tag_repo.get_by_pk(tag_pk)
        if not tag:
            raise ValueError(f"Tag with PK {tag_pk} not found")

        return await self.topic_tag_repo.remove_tag_from_topic(topic_pk, tag_pk)

    async def remove_all_tags_from_topic(self, topic_pk: UUID) -> int:
        """Remove all tags from a topic."""
        # Verify topic exists
        topic = await self.topic_repo.get_by_pk(topic_pk)
        if not topic:
            raise ValueError(f"Topic with PK {topic_pk} not found")

        return await self.topic_tag_repo.remove_all_tags_from_topic(topic_pk)

    async def get_tags_for_topic(self, topic_pk: UUID) -> list[TopicTagWithDetails]:
        """Get all tags for a specific topic."""
        return await self.topic_tag_repo.get_tags_for_topic(topic_pk)

    async def get_topics_by_tag(
        self, tag_pk: UUID, limit: int = 50, offset: int = 0
    ) -> list[UUID]:
        """Get topic PKs that have a specific tag."""
        # Verify tag exists
        tag = await self.tag_repo.get_by_pk(tag_pk)
        if not tag:
            raise ValueError(f"Tag with PK {tag_pk} not found")

        return await self.topic_tag_repo.get_topics_by_tag(
            tag_pk, limit=limit, offset=offset
        )

    async def get_topics_by_tag_name(
        self, tag_name: str, limit: int = 50, offset: int = 0
    ) -> list[UUID]:
        """Get topic PKs that have a specific tag by name."""
        tag = await self.tag_repo.get_by_name(tag_name)
        if not tag:
            raise ValueError(f"Tag with name '{tag_name}' not found")

        return await self.topic_tag_repo.get_topics_by_tag(
            tag.pk, limit=limit, offset=offset
        )

    async def get_tag_usage_stats(self) -> dict[str, int]:
        """Get statistics about tag usage."""
        return await self.topic_tag_repo.get_tag_usage_stats()


# Dependency injection
def get_tag_service() -> TagService:
    """Get tag service instance."""
    return TagService()
