"""Basic unit tests for Admin Dashboard components."""

from datetime import UTC
from datetime import datetime
from uuid import uuid4

from therobotoverlord_api.database.models.admin_action import AdminAction
from therobotoverlord_api.database.models.admin_action import AdminActionCreate
from therobotoverlord_api.database.models.admin_action import AdminActionType
from therobotoverlord_api.database.models.dashboard_snapshot import DashboardSnapshot
from therobotoverlord_api.database.models.dashboard_snapshot import (
    DashboardSnapshotCreate,
)
from therobotoverlord_api.database.models.dashboard_snapshot import (
    DashboardSnapshotType,
)
from therobotoverlord_api.database.models.system_announcement import AnnouncementCreate
from therobotoverlord_api.database.models.system_announcement import AnnouncementType
from therobotoverlord_api.database.models.system_announcement import SystemAnnouncement
from therobotoverlord_api.database.repositories.admin_action import (
    AdminActionRepository,
)
from therobotoverlord_api.database.repositories.dashboard import DashboardRepository
from therobotoverlord_api.database.repositories.system_announcement import (
    SystemAnnouncementRepository,
)


class TestAdminDashboardModels:
    """Test admin dashboard models."""

    def test_admin_action_create_model(self):
        """Test AdminActionCreate model validation."""
        action_create = AdminActionCreate(
            admin_pk=uuid4(),
            action_type=AdminActionType.USER_ROLE_CHANGE,
            target_type="user",
            target_pk=uuid4(),
            description="Test admin action",
            metadata={"test": "data"},
            ip_address="127.0.0.1",
        )

        assert action_create.admin_pk is not None
        assert action_create.action_type == AdminActionType.USER_ROLE_CHANGE
        assert action_create.target_type == "user"
        assert action_create.description == "Test admin action"
        assert action_create.metadata == {"test": "data"}
        assert action_create.ip_address == "127.0.0.1"

    def test_admin_action_model(self):
        """Test AdminAction model validation."""
        admin_action = AdminAction(
            pk=uuid4(),
            admin_pk=uuid4(),
            action_type=AdminActionType.USER_BAN,
            target_type="user",
            target_pk=uuid4(),
            description="User banned for violation",
            metadata={"reason": "spam"},
            ip_address="192.168.1.1",
            created_at=datetime.now(UTC),
            updated_at=None,
        )

        assert admin_action.pk is not None
        assert admin_action.action_type == AdminActionType.USER_BAN
        assert admin_action.description == "User banned for violation"
        assert admin_action.metadata == {"reason": "spam"}

    def test_dashboard_snapshot_create_model(self):
        """Test DashboardSnapshotCreate model validation."""
        snapshot_create = DashboardSnapshotCreate(
            snapshot_type=DashboardSnapshotType.DAILY,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
            metrics_data={"users": 100, "posts": 50},
        )

        assert snapshot_create.snapshot_type == DashboardSnapshotType.DAILY
        assert snapshot_create.metrics_data == {"users": 100, "posts": 50}

    def test_dashboard_snapshot_model(self):
        """Test DashboardSnapshot model validation."""
        snapshot = DashboardSnapshot(
            pk=uuid4(),
            snapshot_type=DashboardSnapshotType.WEEKLY,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
            metrics_data={"active_users": 75, "new_posts": 25},
            generated_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=None,
        )

        assert snapshot.pk is not None
        assert snapshot.snapshot_type == DashboardSnapshotType.WEEKLY
        assert snapshot.metrics_data == {"active_users": 75, "new_posts": 25}

    def test_system_announcement_create_model(self):
        """Test AnnouncementCreate model validation."""
        from therobotoverlord_api.database.models.base import UserRole

        announcement_create = AnnouncementCreate(
            title="System Maintenance",
            content="Scheduled maintenance tonight",
            announcement_type=AnnouncementType.MAINTENANCE,
            target_roles=[UserRole.ADMIN, UserRole.MODERATOR],
            expires_at=datetime.now(UTC),
        )

        assert announcement_create.title == "System Maintenance"
        assert announcement_create.content == "Scheduled maintenance tonight"
        assert announcement_create.announcement_type == AnnouncementType.MAINTENANCE
        assert announcement_create.target_roles == [UserRole.ADMIN, UserRole.MODERATOR]

    def test_system_announcement_model(self):
        """Test SystemAnnouncement model validation."""
        from therobotoverlord_api.database.models.base import UserRole

        announcement = SystemAnnouncement(
            pk=uuid4(),
            title="New Feature Available",
            content="Check out our new dashboard features",
            announcement_type=AnnouncementType.FEATURE_UPDATE,
            created_by_pk=uuid4(),
            target_roles=[UserRole.CITIZEN],
            is_active=True,
            expires_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=None,
        )

        assert announcement.pk is not None
        assert announcement.title == "New Feature Available"
        assert announcement.is_active is True
        assert announcement.announcement_type == AnnouncementType.FEATURE_UPDATE


class TestAdminDashboardRepositories:
    """Test admin dashboard repository initialization."""

    def test_admin_action_repository_init(self):
        """Test AdminActionRepository initialization."""
        repository = AdminActionRepository()
        assert repository.table_name == "admin_actions"

    def test_dashboard_repository_init(self):
        """Test DashboardRepository initialization."""
        repository = DashboardRepository()
        assert repository.table_name == "dashboard_snapshots"

    def test_system_announcement_repository_init(self):
        """Test SystemAnnouncementRepository initialization."""
        repository = SystemAnnouncementRepository()
        assert repository.table_name == "system_announcements"


class TestAdminActionTypes:
    """Test AdminActionType enum values."""

    def test_admin_action_type_values(self):
        """Test AdminActionType enum has expected values."""
        expected_types = [
            "dashboard_access",
            "user_role_change",
            "user_ban",
            "user_unban",
            "sanction_apply",
            "sanction_remove",
            "content_restore",
            "content_delete",
            "appeal_decision",
            "flag_decision",
            "system_config",
            "bulk_action",
        ]

        actual_types = [action_type.value for action_type in AdminActionType]

        for expected_type in expected_types:
            assert expected_type in actual_types

    def test_admin_action_type_enum_usage(self):
        """Test AdminActionType enum can be used in models."""
        action_create = AdminActionCreate(
            admin_pk=uuid4(),
            action_type=AdminActionType.SANCTION_APPLY,
            description="Applied sanction to user",
        )

        assert action_create.action_type == AdminActionType.SANCTION_APPLY
        assert action_create.action_type.value == "sanction_apply"


class TestDashboardSnapshotTypes:
    """Test DashboardSnapshotType enum values."""

    def test_dashboard_snapshot_type_values(self):
        """Test DashboardSnapshotType enum has expected values."""
        expected_types = ["daily", "weekly", "monthly"]
        actual_types = [snapshot_type.value for snapshot_type in DashboardSnapshotType]

        for expected_type in expected_types:
            assert expected_type in actual_types

    def test_dashboard_snapshot_type_enum_usage(self):
        """Test DashboardSnapshotType enum can be used in models."""
        snapshot_create = DashboardSnapshotCreate(
            snapshot_type=DashboardSnapshotType.MONTHLY,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
            metrics_data={"total_users": 1000},
        )

        assert snapshot_create.snapshot_type == DashboardSnapshotType.MONTHLY
        assert snapshot_create.snapshot_type.value == "monthly"
