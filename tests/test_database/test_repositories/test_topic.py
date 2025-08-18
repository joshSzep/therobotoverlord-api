"""Tests for topic repositories."""

from datetime import UTC
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.base import TopicStatus
from therobotoverlord_api.database.models.topic import Topic
from therobotoverlord_api.database.models.topic import TopicCreate
from therobotoverlord_api.database.models.topic import TopicSummary
from therobotoverlord_api.database.models.topic import TopicUpdate
from therobotoverlord_api.database.repositories.topic import TopicRepository


@pytest.mark.asyncio
class TestTopicRepository:
    """Test TopicRepository class."""

    @pytest.fixture
    def topic_repository(self):
        """Create TopicRepository instance."""
        return TopicRepository()

    @pytest.fixture
    def sample_topic_create(self):
        """Create sample TopicCreate data."""
        return TopicCreate(
            title="Test Topic",
            description="A test topic for discussion",
            author_pk=uuid4(),
        )

    @pytest.fixture
    def overlord_topic_create(self):
        """Create sample Overlord TopicCreate data."""
        return TopicCreate(
            title="Overlord Topic",
            description="Created by the Overlord",
            author_pk=uuid4(),
            created_by_overlord=True,
        )

    async def test_create_topic(
        self, topic_repository, sample_topic_create, mock_connection
    ):
        """Test creating a topic."""
        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            # Mock the database response
            topic_pk = uuid4()
            created_at = datetime.now(UTC)

            mock_record = {
                "pk": topic_pk,
                "created_at": created_at,
                "updated_at": None,
                "title": sample_topic_create.title,
                "description": sample_topic_create.description,
                "author_pk": sample_topic_create.author_pk,
                "status": TopicStatus.PENDING_APPROVAL.value,
                "approved_at": None,
                "approved_by": None,
                "created_by_overlord": False,
            }

            mock_connection.fetchrow.return_value = mock_record

            # Create topic
            result = await topic_repository.create(sample_topic_create)

        # Assertions
        assert isinstance(result, Topic)
        assert result.title == sample_topic_create.title
        assert result.description == sample_topic_create.description
        assert result.author_pk == sample_topic_create.author_pk
        assert result.status == TopicStatus.PENDING_APPROVAL
        assert result.created_by_overlord is False

        # Verify database call
        mock_connection.fetchrow.assert_called_once()

    async def test_create_overlord_topic(
        self, topic_repository, overlord_topic_create, mock_connection
    ):
        """Test creating an Overlord topic."""
        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            topic_pk = uuid4()
            created_at = datetime.now(UTC)

            mock_record = {
                "pk": topic_pk,
                "created_at": created_at,
                "updated_at": None,
                "title": overlord_topic_create.title,
                "description": overlord_topic_create.description,
                "author_pk": overlord_topic_create.author_pk,
                "status": TopicStatus.APPROVED.value,
                "approved_at": created_at,
                "approved_by": overlord_topic_create.author_pk,
                "created_by_overlord": True,
            }

            mock_connection.fetchrow.return_value = mock_record

            result = await topic_repository.create(overlord_topic_create)

        assert result.created_by_overlord is True
        assert result.status == TopicStatus.APPROVED

    async def test_update_topic(self, topic_repository, mock_connection):
        """Test updating a topic."""
        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            topic_pk = uuid4()
            topic_update = TopicUpdate(
                title="Updated Title",
                description="Updated description",
            )

            updated_at = datetime.now(UTC)
            mock_record = {
                "pk": topic_pk,
                "created_at": datetime.now(UTC),
                "updated_at": updated_at,
                "title": topic_update.title,
                "description": topic_update.description,
                "author_pk": uuid4(),
                "status": TopicStatus.PENDING_APPROVAL.value,
                "approved_at": None,
                "approved_by": None,
                "created_by_overlord": False,
            }

            mock_connection.fetchrow.return_value = mock_record

            result = await topic_repository.update(topic_pk, topic_update)

        assert result.title == topic_update.title
        assert result.description == topic_update.description
        assert result.updated_at == updated_at

    async def test_get_by_status(self, topic_repository, mock_connection):
        """Test getting topics by status."""
        with patch(
            "therobotoverlord_api.database.repositories.topic.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_records = [
                {
                    "pk": uuid4(),
                    "created_at": datetime.now(UTC),
                    "updated_at": None,
                    "title": "Pending Topic 1",
                    "description": "Description 1",
                    "author_pk": uuid4(),
                    "status": TopicStatus.PENDING_APPROVAL.value,
                    "approved_at": None,
                    "approved_by": None,
                    "created_by_overlord": False,
                },
                {
                    "pk": uuid4(),
                    "created_at": datetime.now(UTC),
                    "updated_at": None,
                    "title": "Pending Topic 2",
                    "description": "Description 2",
                    "author_pk": uuid4(),
                    "status": TopicStatus.PENDING_APPROVAL.value,
                    "approved_at": None,
                    "approved_by": None,
                    "created_by_overlord": False,
                },
            ]

            mock_connection.fetch.return_value = mock_records

            result = await topic_repository.get_by_status(
                TopicStatus.PENDING_APPROVAL, limit=10, offset=0
            )

        assert len(result) == 2
        assert all(isinstance(topic, Topic) for topic in result)
        assert all(topic.status == TopicStatus.PENDING_APPROVAL for topic in result)

    async def test_get_with_author_info(self, topic_repository, mock_connection):
        """Test getting topics with author information."""
        with patch(
            "therobotoverlord_api.database.repositories.topic.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_records = [
                {
                    "pk": uuid4(),
                    "title": "Test Topic",
                    "description": "Test Description",
                    "author_pk": uuid4(),
                    "status": TopicStatus.APPROVED.value,
                    "approved_at": datetime.now(UTC),
                    "approved_by": uuid4(),
                    "created_by_overlord": False,
                    "created_at": datetime.now(UTC),
                    "author_username": "testuser",
                }
            ]

            mock_connection.fetch.return_value = mock_records

            result = await topic_repository.get_approved_topics(limit=10, offset=0)

        assert len(result) == 1
        assert isinstance(result[0], TopicSummary)
        assert result[0].author_username == "testuser"

    async def test_get_by_author(self, topic_repository, mock_connection):
        """Test getting topics by author."""
        with patch(
            "therobotoverlord_api.database.repositories.topic.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            author_pk = uuid4()
            mock_records = [
                {
                    "pk": uuid4(),
                    "title": "Author Topic",
                    "description": "Test Description",
                    "author_pk": author_pk,
                    "status": TopicStatus.APPROVED.value,
                    "approved_at": datetime.now(UTC),
                    "approved_by": uuid4(),
                    "created_by_overlord": False,
                    "created_at": datetime.now(UTC),
                    "updated_at": None,
                }
            ]

            mock_connection.fetch.return_value = mock_records

            result = await topic_repository.get_by_author(author_pk, limit=10, offset=0)

        assert len(result) == 1
        assert isinstance(result[0], TopicSummary)
        assert result[0].author_pk == author_pk

    async def test_search_topics(self, topic_repository, mock_connection):
        """Test searching topics."""
        with patch(
            "therobotoverlord_api.database.repositories.topic.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_records = [
                {
                    "pk": uuid4(),
                    "title": "Robot Overlord Topic",
                    "description": "Robot overlord discussion",
                    "author_pk": uuid4(),
                    "status": TopicStatus.APPROVED.value,
                    "approved_at": datetime.now(UTC),
                    "approved_by": uuid4(),
                    "created_by_overlord": False,
                    "created_at": datetime.now(UTC),
                    "author_username": "testuser",
                }
            ]

            mock_connection.fetch.return_value = mock_records

            result = await topic_repository.search_topics("robot", limit=10, offset=0)

        assert len(result) == 1
        assert isinstance(result[0], TopicSummary)
        assert "robot" in result[0].description.lower()

    async def test_approve_topic(self, topic_repository, mock_connection):
        """Test approving a topic."""
        with patch(
            "therobotoverlord_api.database.repositories.topic.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            topic_pk = uuid4()
            approved_by = uuid4()
            approved_at = datetime.now(UTC)

            mock_record = {
                "pk": topic_pk,
                "created_at": datetime.now(UTC),
                "updated_at": approved_at,
                "title": "Test Topic",
                "description": "Test Description",
                "author_pk": uuid4(),
                "status": TopicStatus.APPROVED.value,
                "approved_at": approved_at,
                "approved_by": approved_by,
                "created_by_overlord": False,
            }

            mock_connection.fetchrow.return_value = mock_record

            result = await topic_repository.approve_topic(topic_pk, approved_by)

        assert result.status == TopicStatus.APPROVED
        assert result.approved_by == approved_by
        assert result.approved_at == approved_at

    async def test_get_overlord_created_topics(self, topic_repository, mock_connection):
        """Test getting Overlord-created topics."""
        with patch(
            "therobotoverlord_api.database.repositories.topic.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_records = [
                {
                    "pk": uuid4(),
                    "title": "Overlord Topic",
                    "description": "Created by Overlord",
                    "author_pk": uuid4(),
                    "status": TopicStatus.APPROVED.value,
                    "created_at": datetime.now(UTC),
                    "created_by_overlord": True,
                    "author_username": "overlord",
                }
            ]

            mock_connection.fetch.return_value = mock_records

            result = await topic_repository.get_overlord_topics(limit=10, offset=0)

        assert len(result) == 1
        assert isinstance(result[0], TopicSummary)
        assert result[0].created_by_overlord is True

    async def test_get_nonexistent_topic(self, topic_repository, mock_connection):
        """Test getting a non-existent topic."""
        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.return_value = None

            result = await topic_repository.get_by_pk(uuid4())

            assert result is None

    async def test_update_nonexistent_topic(self, topic_repository, mock_connection):
        """Test updating a non-existent topic."""
        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.return_value = None

            topic_update = TopicUpdate(title="New Title")
            result = await topic_repository.update(uuid4(), topic_update)

        assert result is None

    async def test_delete_topic(self, topic_repository, mock_connection):
        """Test deleting a topic."""
        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            topic_pk = uuid4()
            mock_connection.execute.return_value = "DELETE 1"

            result = await topic_repository.delete_by_pk(topic_pk)

            assert result is True
            mock_connection.execute.assert_called_once()

    async def test_delete_nonexistent_topic(self, topic_repository, mock_connection):
        """Test deleting a non-existent topic."""
        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            topic_pk = uuid4()
            mock_connection.execute.return_value = "DELETE 0"

            result = await topic_repository.delete_by_pk(topic_pk)

            assert result is False
