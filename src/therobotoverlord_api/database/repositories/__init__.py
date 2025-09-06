"""Database repositories for The Robot Overlord API."""

from therobotoverlord_api.database.repositories.base import BaseRepository
from therobotoverlord_api.database.repositories.post import PostRepository
from therobotoverlord_api.database.repositories.private_message import (
    PrivateMessageRepository,
)
from therobotoverlord_api.database.repositories.queue import (
    PostModerationQueueRepository,
)
from therobotoverlord_api.database.repositories.queue import (
    PrivateMessageQueueRepository,
)
from therobotoverlord_api.database.repositories.queue import QueueOverviewRepository
from therobotoverlord_api.database.repositories.queue import (
    TopicCreationQueueRepository,
)
from therobotoverlord_api.database.repositories.tag import TagRepository
from therobotoverlord_api.database.repositories.tag import TopicTagRepository
from therobotoverlord_api.database.repositories.topic import TopicRepository
from therobotoverlord_api.database.repositories.user import get_user_repository
from therobotoverlord_api.database.repositories.user_session import (
    get_user_session_repository,
)

__all__ = [
    "BaseRepository",
    "PostModerationQueueRepository",
    "PostRepository",
    "PrivateMessageQueueRepository",
    "PrivateMessageRepository",
    "QueueOverviewRepository",
    "TagRepository",
    "TopicCreationQueueRepository",
    "TopicRepository",
    "TopicTagRepository",
    "get_user_repository",
    "get_user_session_repository",
]
