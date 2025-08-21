"""Test fixtures for tag-related tests."""

from datetime import UTC
from datetime import datetime
from uuid import UUID
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.base import TopicStatus
from therobotoverlord_api.database.models.tag import Tag
from therobotoverlord_api.database.models.tag import TagCreate
from therobotoverlord_api.database.models.tag import TagDetail
from therobotoverlord_api.database.models.tag import TopicTag
from therobotoverlord_api.database.models.tag import TopicTagCreate
from therobotoverlord_api.database.models.topic import TopicSummary
from therobotoverlord_api.database.models.topic import TopicWithAuthor


@pytest.fixture
def tag_politics():
    """Politics tag fixture."""
    return Tag(
        pk=uuid4(),
        name="politics",
        description="Political discussions and debates",
        color="#FF0000",
        created_at=datetime.now(UTC),
        updated_at=None,
    )


@pytest.fixture
def tag_technology():
    """Technology tag fixture."""
    return Tag(
        pk=uuid4(),
        name="technology",
        description="Technology and innovation discussions",
        color="#00FF00",
        created_at=datetime.now(UTC),
        updated_at=None,
    )


@pytest.fixture
def tag_science():
    """Science tag fixture."""
    return Tag(
        pk=uuid4(),
        name="science",
        description="Scientific research and discoveries",
        color="#0000FF",
        created_at=datetime.now(UTC),
        updated_at=None,
    )


@pytest.fixture
def tag_debate():
    """Debate tag fixture."""
    return Tag(
        pk=uuid4(),
        name="debate",
        description="Debate and argumentation",
        color="#FF00FF",
        created_at=datetime.now(UTC),
        updated_at=None,
    )


@pytest.fixture
def tag_controversial():
    """Controversial tag fixture."""
    return Tag(
        pk=uuid4(),
        name="controversial",
        description="Controversial topics requiring careful moderation",
        color="#FFA500",
        created_at=datetime.now(UTC),
        updated_at=None,
    )


@pytest.fixture
def all_tags(tag_politics, tag_technology, tag_science, tag_debate, tag_controversial):
    """All tag fixtures as a list."""
    return [tag_politics, tag_technology, tag_science, tag_debate, tag_controversial]


@pytest.fixture
def tag_detail_politics():
    """Politics tag detail with topic count."""
    return TagDetail(
        pk=uuid4(),
        name="politics",
        description="Political discussions and debates",
        color="#FF0000",
        created_at=datetime.now(UTC),
        updated_at=None,
        topic_count=15,
    )


@pytest.fixture
def tag_detail_technology():
    """Technology tag detail with topic count."""
    return TagDetail(
        pk=uuid4(),
        name="technology",
        description="Technology and innovation discussions",
        color="#00FF00",
        created_at=datetime.now(UTC),
        updated_at=None,
        topic_count=8,
    )


@pytest.fixture
def tag_detail_science():
    """Science tag detail with topic count."""
    return TagDetail(
        pk=uuid4(),
        name="science",
        description="Scientific research and discoveries",
        color="#0000FF",
        created_at=datetime.now(UTC),
        updated_at=None,
        topic_count=12,
    )


@pytest.fixture
def popular_tags(tag_detail_politics, tag_detail_technology, tag_detail_science):
    """Popular tags ordered by topic count."""
    return [tag_detail_politics, tag_detail_science, tag_detail_technology]


@pytest.fixture
def tag_create_data():
    """Sample tag creation data."""
    return {
        "name": "new-tag",
        "description": "A newly created tag",
        "color": "#ABCDEF",
    }


@pytest.fixture
def tag_create_minimal():
    """Minimal tag creation data."""
    return TagCreate(name="minimal-tag")


@pytest.fixture
def tag_create_full():
    """Full tag creation data."""
    return TagCreate(
        name="full-tag",
        description="A tag with all fields",
        color="#123456",
    )


@pytest.fixture
def topic_tag_relationship(tag_politics):
    """Topic-tag relationship fixture."""
    return TopicTag(
        pk=uuid4(),
        topic_pk=uuid4(),
        tag_pk=tag_politics.pk,
        created_at=datetime.now(UTC),
        updated_at=None,
    )


@pytest.fixture
def topic_tag_create_data():
    """Topic-tag creation data."""
    return TopicTagCreate(
        topic_pk=uuid4(),
        tag_pk=uuid4(),
    )


@pytest.fixture
def sample_topic_with_tags():
    """Sample topic with tags for testing."""
    return TopicWithAuthor(
        pk=uuid4(),
        title="Sample Tagged Topic",
        description="A topic with multiple tags for testing",
        author_pk=uuid4(),
        author_username="testuser",
        created_by_overlord=False,
        status=TopicStatus.APPROVED,
        approved_at=None,
        approved_by=None,
        created_at=datetime.now(UTC),
        updated_at=None,
        tags=["politics", "debate", "controversial"],
    )


@pytest.fixture
def sample_topics_with_various_tags():
    """Multiple topics with different tag combinations."""
    return [
        TopicSummary(
            pk=uuid4(),
            title="Political Debate",
            description="A heated political discussion",
            author_username="debater1",
            created_by_overlord=False,
            status=TopicStatus.APPROVED,
            created_at=datetime.now(UTC),
            post_count=15,
            tags=["politics", "debate", "controversial"],
        ),
        TopicSummary(
            pk=uuid4(),
            title="Tech Innovation",
            description="Latest in technology",
            author_username="techie",
            created_by_overlord=False,
            status=TopicStatus.APPROVED,
            created_at=datetime.now(UTC),
            post_count=8,
            tags=["technology", "innovation"],
        ),
        TopicSummary(
            pk=uuid4(),
            title="Scientific Research",
            description="New scientific discoveries",
            author_username="scientist",
            created_by_overlord=True,
            status=TopicStatus.APPROVED,
            created_at=datetime.now(UTC),
            post_count=22,
            tags=["science", "research"],
        ),
        TopicSummary(
            pk=uuid4(),
            title="Tech Politics",
            description="Technology policy and regulation",
            author_username="policy_expert",
            created_by_overlord=False,
            status=TopicStatus.APPROVED,
            created_at=datetime.now(UTC),
            post_count=12,
            tags=["technology", "politics", "policy"],
        ),
        TopicSummary(
            pk=uuid4(),
            title="Untagged Topic",
            description="A topic without any tags",
            author_username="simple_user",
            created_by_overlord=False,
            status=TopicStatus.APPROVED,
            created_at=datetime.now(UTC),
            post_count=3,
            tags=[],
        ),
    ]


@pytest.fixture
def tag_usage_stats():
    """Sample tag usage statistics."""
    return {
        "total_tags": 25,
        "used_tags": 18,
        "unused_tags": 7,
        "avg_tags_per_topic": 2.3,
        "most_popular_tag": "politics",
        "least_popular_tag": "niche-topic",
        "topics_with_tags": 45,
        "topics_without_tags": 5,
    }


@pytest.fixture
def tag_search_results(tag_politics, tag_technology):
    """Sample tag search results."""
    return [tag_politics, tag_technology]


@pytest.fixture
def related_topics_by_tags():
    """Topics related by shared tags."""
    return [
        TopicSummary(
            pk=uuid4(),
            title="Related Political Topic 1",
            description="Another political discussion",
            author_username="politician1",
            created_by_overlord=False,
            status=TopicStatus.APPROVED,
            created_at=datetime.now(UTC),
            post_count=18,
            tags=["politics", "government"],
        ),
        TopicSummary(
            pk=uuid4(),
            title="Related Political Topic 2",
            description="Yet another political discussion",
            author_username="politician2",
            created_by_overlord=False,
            status=TopicStatus.APPROVED,
            created_at=datetime.now(UTC),
            post_count=9,
            tags=["politics", "election"],
        ),
        TopicSummary(
            pk=uuid4(),
            title="Debate Techniques",
            description="How to debate effectively",
            author_username="debate_coach",
            created_by_overlord=False,
            status=TopicStatus.APPROVED,
            created_at=datetime.now(UTC),
            post_count=14,
            tags=["debate", "education"],
        ),
    ]


# Factory functions for dynamic fixture creation


def create_tag(
    name: str, description: str | None = None, color: str | None = None
) -> Tag:
    """Factory function to create a tag with custom parameters."""
    return Tag(
        pk=uuid4(),
        name=name,
        description=description,
        color=color,
        created_at=datetime.now(UTC),
        updated_at=None,
    )


def create_tag_detail(
    name: str,
    topic_count: int,
    description: str | None = None,
    color: str | None = None,
) -> TagDetail:
    """Factory function to create a tag detail with custom parameters."""
    return TagDetail(
        pk=uuid4(),
        name=name,
        description=description,
        color=color,
        created_at=datetime.now(UTC),
        updated_at=None,
        topic_count=topic_count,
    )


def create_topic_with_tags(title: str, tags: list[str], **kwargs) -> TopicSummary:
    """Factory function to create a topic with specific tags."""
    defaults = {
        "pk": uuid4(),
        "description": f"Description for {title}",
        "author_username": "testuser",
        "created_by_overlord": False,
        "status": TopicStatus.APPROVED,
        "created_at": datetime.now(UTC),
        "post_count": 5,
    }
    defaults.update(kwargs)

    return TopicSummary(
        pk=defaults["pk"],
        title=title,
        description=defaults["description"],
        author_username=defaults["author_username"],
        created_by_overlord=defaults["created_by_overlord"],
        status=defaults["status"],
        created_at=defaults["created_at"],
        post_count=defaults["post_count"],
        tags=tags,
    )


def create_topic_tag_relationship(
    topic_pk: UUID | None = None, tag_pk: UUID | None = None
) -> TopicTag:
    """Factory function to create a topic-tag relationship."""
    return TopicTag(
        pk=uuid4(),
        topic_pk=topic_pk or uuid4(),
        tag_pk=tag_pk or uuid4(),
        created_at=datetime.now(UTC),
        updated_at=None,
    )


# Parametrized fixtures for testing multiple scenarios


@pytest.fixture(
    params=[
        ("politics", "#FF0000", "Political discussions"),
        ("technology", "#00FF00", "Tech discussions"),
        ("science", "#0000FF", "Scientific topics"),
    ]
)
def parametrized_tag(request):
    """Parametrized tag fixture for testing multiple tag types."""
    name, color, description = request.param
    return create_tag(name=name, color=color, description=description)


@pytest.fixture(
    params=[
        (["politics"], 1),
        (["politics", "debate"], 2),
        (["technology", "innovation", "future"], 3),
        ([], 0),
    ]
)
def parametrized_topic_with_tags(request):
    """Parametrized topic fixture with different tag combinations."""
    tags, expected_count = request.param
    topic = create_topic_with_tags(
        title=f"Topic with {expected_count} tags",
        tags=tags,
    )
    return topic, expected_count


@pytest.fixture(params=[1, 5, 10, 25])
def parametrized_topic_count(request):
    """Parametrized fixture for different topic counts."""
    return request.param
