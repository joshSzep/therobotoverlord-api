"""Tests for tag models."""

from datetime import UTC
from datetime import datetime
from uuid import uuid4

from therobotoverlord_api.database.models.tag import Tag
from therobotoverlord_api.database.models.tag import TagCreate
from therobotoverlord_api.database.models.tag import TagDetail
from therobotoverlord_api.database.models.tag import TagUpdate
from therobotoverlord_api.database.models.tag import TopicTag
from therobotoverlord_api.database.models.tag import TopicTagCreate


class TestTag:
    """Test Tag model."""

    def test_tag_creation(self):
        """Test creating a Tag instance."""
        pk = uuid4()
        created_at = datetime.now(UTC)

        tag = Tag(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            name="politics",
            description="Political discussions and debates",
            color="#FF0000",
        )

        assert tag.pk == pk
        assert tag.name == "politics"
        assert tag.description == "Political discussions and debates"
        assert tag.color == "#FF0000"
        assert tag.created_at == created_at
        assert tag.updated_at is None

    def test_tag_minimal(self):
        """Test Tag with minimal required fields."""
        pk = uuid4()
        created_at = datetime.now(UTC)

        tag = Tag(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            name="technology",
            description=None,
            color=None,
        )

        assert tag.name == "technology"
        assert tag.description is None
        assert tag.color is None

    def test_tag_with_color_validation(self):
        """Test Tag with various color formats."""
        pk = uuid4()
        created_at = datetime.now(UTC)

        # Valid hex color
        tag = Tag(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            name="test",
            description="Test tag",
            color="#00FF00",
        )
        assert tag.color == "#00FF00"


class TestTagCreate:
    """Test TagCreate model."""

    def test_tag_create_valid(self):
        """Test creating a valid TagCreate instance."""
        tag_create = TagCreate(
            name="science",
            description="Scientific discussions",
            color="#0000FF",
        )

        assert tag_create.name == "science"
        assert tag_create.description == "Scientific discussions"
        assert tag_create.color == "#0000FF"

    def test_tag_create_minimal(self):
        """Test TagCreate with only required fields."""
        tag_create = TagCreate(name="minimal")

        assert tag_create.name == "minimal"
        assert tag_create.description is None
        assert tag_create.color is None

    def test_tag_create_name_validation(self):
        """Test name validation."""
        # Valid name
        tag_create = TagCreate(name="valid-tag_name123")
        assert tag_create.name == "valid-tag_name123"

        # Empty name should be allowed at Pydantic level
        tag_create = TagCreate(name="")
        assert tag_create.name == ""

    def test_tag_create_description_length(self):
        """Test description length handling."""
        long_description = "A" * 500
        tag_create = TagCreate(
            name="test",
            description=long_description,
        )
        assert tag_create.description == long_description


class TestTagUpdate:
    """Test TagUpdate model."""

    def test_tag_update_partial(self):
        """Test partial update."""
        tag_update = TagUpdate(name="updated-name")

        assert tag_update.name == "updated-name"
        assert tag_update.description is None
        assert tag_update.color is None

    def test_tag_update_full(self):
        """Test full update."""
        tag_update = TagUpdate(
            name="fully-updated",
            description="Updated description",
            color="#FFFF00",
        )

        assert tag_update.name == "fully-updated"
        assert tag_update.description == "Updated description"
        assert tag_update.color == "#FFFF00"

    def test_tag_update_description_only(self):
        """Test updating only description."""
        tag_update = TagUpdate(description="New description")

        assert tag_update.description == "New description"
        assert tag_update.name is None
        assert tag_update.color is None

    def test_tag_update_color_only(self):
        """Test updating only color."""
        tag_update = TagUpdate(color="#00FFFF")

        assert tag_update.color == "#00FFFF"
        assert tag_update.name is None
        assert tag_update.description is None


class TestTagDetail:
    """Test TagDetail model."""

    def test_tag_detail_creation(self):
        """Test creating TagDetail instance."""
        pk = uuid4()
        created_at = datetime.now(UTC)

        tag_detail = TagDetail(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            name="detailed-tag",
            description="A detailed tag",
            color="#FF00FF",
            topic_count=15,
        )

        assert tag_detail.pk == pk
        assert tag_detail.name == "detailed-tag"
        assert tag_detail.description == "A detailed tag"
        assert tag_detail.color == "#FF00FF"
        assert tag_detail.topic_count == 15

    def test_tag_detail_zero_topics(self):
        """Test TagDetail with zero topics."""
        pk = uuid4()
        created_at = datetime.now(UTC)

        tag_detail = TagDetail(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            name="unused-tag",
            description="An unused tag",
            color=None,
            topic_count=0,
        )

        assert tag_detail.topic_count == 0


class TestTopicTag:
    """Test TopicTag model."""

    def test_topic_tag_creation(self):
        """Test creating a TopicTag instance."""
        pk = uuid4()
        topic_pk = uuid4()
        tag_pk = uuid4()
        created_at = datetime.now(UTC)

        topic_tag = TopicTag(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            topic_pk=topic_pk,
            tag_pk=tag_pk,
        )

        assert topic_tag.pk == pk
        assert topic_tag.topic_pk == topic_pk
        assert topic_tag.tag_pk == tag_pk
        assert topic_tag.created_at == created_at
        assert topic_tag.updated_at is None

    def test_topic_tag_relationship(self):
        """Test TopicTag represents correct relationship."""
        topic_pk = uuid4()
        tag_pk = uuid4()

        topic_tag = TopicTag(
            pk=uuid4(),
            created_at=datetime.now(UTC),
            updated_at=None,
            topic_pk=topic_pk,
            tag_pk=tag_pk,
        )

        # Verify the relationship is correctly stored
        assert topic_tag.topic_pk == topic_pk
        assert topic_tag.tag_pk == tag_pk


class TestTopicTagCreate:
    """Test TopicTagCreate model."""

    def test_topic_tag_create_valid(self):
        """Test creating a valid TopicTagCreate instance."""
        topic_pk = uuid4()
        tag_pk = uuid4()

        topic_tag_create = TopicTagCreate(
            topic_pk=topic_pk,
            tag_pk=tag_pk,
        )

        assert topic_tag_create.topic_pk == topic_pk
        assert topic_tag_create.tag_pk == tag_pk

    def test_topic_tag_create_different_uuids(self):
        """Test TopicTagCreate with different UUIDs."""
        topic_pk1 = uuid4()
        topic_pk2 = uuid4()
        tag_pk1 = uuid4()
        tag_pk2 = uuid4()

        # First relationship
        topic_tag1 = TopicTagCreate(topic_pk=topic_pk1, tag_pk=tag_pk1)

        # Second relationship
        topic_tag2 = TopicTagCreate(topic_pk=topic_pk2, tag_pk=tag_pk2)

        # Verify they're different
        assert topic_tag1.topic_pk != topic_tag2.topic_pk
        assert topic_tag1.tag_pk != topic_tag2.tag_pk

        # Same topic, different tags
        topic_tag3 = TopicTagCreate(topic_pk=topic_pk1, tag_pk=tag_pk2)
        assert topic_tag3.topic_pk == topic_tag1.topic_pk
        assert topic_tag3.tag_pk != topic_tag1.tag_pk


class TestTagModelIntegration:
    """Test integration between tag models."""

    def test_tag_to_tag_detail_conversion(self):
        """Test converting Tag to TagDetail."""
        pk = uuid4()
        created_at = datetime.now(UTC)

        # Create a Tag
        tag = Tag(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            name="integration-test",
            description="Integration test tag",
            color="#123456",
        )

        # Convert to TagDetail (simulating adding topic count)
        tag_detail = TagDetail(
            pk=tag.pk,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
            name=tag.name,
            description=tag.description,
            color=tag.color,
            topic_count=5,
        )

        assert tag_detail.pk == tag.pk
        assert tag_detail.name == tag.name
        assert tag_detail.description == tag.description
        assert tag_detail.color == tag.color
        assert tag_detail.topic_count == 5

    def test_tag_create_to_tag_conversion(self):
        """Test converting TagCreate to Tag."""
        tag_create = TagCreate(
            name="new-tag",
            description="A new tag",
            color="#ABCDEF",
        )

        # Simulate creating Tag from TagCreate
        pk = uuid4()
        created_at = datetime.now(UTC)

        tag = Tag(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            name=tag_create.name,
            description=tag_create.description,
            color=tag_create.color,
        )

        assert tag.name == tag_create.name
        assert tag.description == tag_create.description
        assert tag.color == tag_create.color

    def test_tag_update_application(self):
        """Test applying TagUpdate to existing Tag."""
        # Original tag
        original_tag = Tag(
            pk=uuid4(),
            created_at=datetime.now(UTC),
            updated_at=None,
            name="original",
            description="Original description",
            color="#000000",
        )

        # Update data
        tag_update = TagUpdate(
            name="updated",
            description="Updated description",
        )

        # Apply update (simulating repository update logic)
        updated_tag = Tag(
            pk=original_tag.pk,
            created_at=original_tag.created_at,
            updated_at=datetime.now(UTC),
            name=tag_update.name or original_tag.name,
            description=tag_update.description or original_tag.description,
            color=tag_update.color or original_tag.color,
        )

        assert updated_tag.pk == original_tag.pk
        assert updated_tag.name == "updated"
        assert updated_tag.description == "Updated description"
        assert updated_tag.color == "#000000"  # Unchanged
        assert updated_tag.updated_at is not None
