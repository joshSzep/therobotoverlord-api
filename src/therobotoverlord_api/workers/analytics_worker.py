"""Analytics aggregation worker for The Robot Overlord."""

import logging

from datetime import UTC
from datetime import datetime
from datetime import timedelta

import asyncpg

from therobotoverlord_api.database.models.dashboard_snapshot import (
    DashboardSnapshotType,
)
from therobotoverlord_api.database.repositories.dashboard import DashboardRepository
from therobotoverlord_api.services.dashboard_service import DashboardService
from therobotoverlord_api.workers.base import BaseWorker
from therobotoverlord_api.workers.base import create_worker_class

logger = logging.getLogger(__name__)


class AnalyticsAggregationWorker(BaseWorker):
    """Worker for aggregating analytics data into dashboard snapshots."""

    def __init__(self):
        super().__init__()
        self.dashboard_service = DashboardService()
        self.dashboard_repo = DashboardRepository()

    async def generate_hourly_snapshot(self, ctx: dict) -> bool:
        """Generate hourly analytics snapshot."""
        return await self._generate_snapshot(ctx, "hourly", hours=1)

    async def generate_daily_snapshot(self, ctx: dict) -> bool:
        """Generate daily analytics snapshot."""
        return await self._generate_snapshot(ctx, "daily", days=1)

    async def generate_weekly_snapshot(self, ctx: dict) -> bool:
        """Generate weekly analytics snapshot."""
        return await self._generate_snapshot(ctx, "weekly", weeks=1)

    async def generate_monthly_snapshot(self, ctx: dict) -> bool:
        """Generate monthly analytics snapshot."""
        return await self._generate_snapshot(ctx, "monthly", days=30)

    async def _generate_snapshot(
        self, ctx: dict, snapshot_type: str, **time_delta_kwargs
    ) -> bool:
        """Generate analytics snapshot for the specified period."""
        try:
            # Ensure database connection is available
            if self.db is None:  # type: ignore[has-type]
                db: asyncpg.Connection | None = ctx.get("db")
                if db and isinstance(db, asyncpg.Connection):
                    self.db = db
                else:
                    logger.error("Database connection not available")
                    return False

            # Calculate period boundaries
            period_end = datetime.now(UTC)
            period_start = period_end - timedelta(**time_delta_kwargs)

            logger.info(
                f"Generating {snapshot_type} snapshot for period {period_start} to {period_end}"
            )

            # Get dashboard overview data
            dashboard_data = await self.dashboard_service.get_dashboard_overview("24h")

            # Create snapshot record
            snapshot_data = {
                "snapshot_type": snapshot_type,
                "metrics_data": dashboard_data.model_dump(),
                "period_start": period_start,
                "period_end": period_end,
                "generated_at": datetime.now(UTC),
            }

            snapshot = await self.dashboard_repo.create_from_dict(snapshot_data)
            if snapshot:
                logger.info(
                    f"Successfully created {snapshot_type} snapshot {snapshot.pk}"
                )
                return True

            logger.error(f"Failed to create {snapshot_type} snapshot")
            return False

        except Exception:
            logger.exception(f"Error generating {snapshot_type} snapshot")
            return False

    async def cleanup_old_snapshots(self, ctx: dict) -> bool:
        """Clean up old dashboard snapshots to manage storage."""
        try:
            # Ensure database connection is available
            if self.db is None:  # type: ignore[has-type]
                db: asyncpg.Connection | None = ctx.get("db")
                if db and isinstance(db, asyncpg.Connection):
                    self.db = db
                else:
                    logger.error("Database connection not available")
                    return False

            # Define retention policies (snapshot_type -> keep_count)
            retention_policies = {
                DashboardSnapshotType.HOURLY: 168,  # Keep 168 hours (1 week)
                DashboardSnapshotType.DAILY: 90,  # Keep 90 days (3 months)
                DashboardSnapshotType.WEEKLY: 52,  # Keep 52 weeks (1 year)
                DashboardSnapshotType.MONTHLY: 36,  # Keep 36 months (3 years)
            }

            total_cleaned = 0
            for snapshot_type, keep_count in retention_policies.items():
                cleaned_count = await self.dashboard_repo.cleanup_old_snapshots(
                    snapshot_type, keep_count
                )
                total_cleaned += cleaned_count
                logger.info(f"Cleaned up {cleaned_count} old {snapshot_type} snapshots")

            logger.info(f"Total snapshots cleaned up: {total_cleaned}")
            return True

        except Exception:
            logger.exception("Error cleaning up old snapshots")
            return False


# Define worker functions
async def generate_hourly_snapshot(ctx: dict) -> bool:
    """Worker function for hourly snapshot generation."""
    try:
        worker = AnalyticsAggregationWorker()
        return await worker.generate_hourly_snapshot(ctx)
    except Exception:
        logger.exception("Error in hourly snapshot generation worker")
        return False


async def generate_daily_snapshot(ctx: dict) -> bool:
    """Worker function for daily snapshot generation."""
    try:
        worker = AnalyticsAggregationWorker()
        return await worker.generate_daily_snapshot(ctx)
    except Exception:
        logger.exception("Error in daily snapshot generation worker")
        return False


async def generate_weekly_snapshot(ctx: dict) -> bool:
    """Worker function for weekly snapshot generation."""
    try:
        worker = AnalyticsAggregationWorker()
        return await worker.generate_weekly_snapshot(ctx)
    except Exception:
        logger.exception("Error in weekly snapshot generation worker")
        return False


async def generate_monthly_snapshot(ctx: dict) -> bool:
    """Worker function for monthly snapshot generation."""
    try:
        worker = AnalyticsAggregationWorker()
        return await worker.generate_monthly_snapshot(ctx)
    except Exception:
        logger.exception("Error in monthly snapshot generation worker")
        return False


async def cleanup_old_snapshots(ctx: dict) -> bool:
    """Worker function for cleaning up old snapshots."""
    try:
        worker = AnalyticsAggregationWorker()
        return await worker.cleanup_old_snapshots(ctx)
    except Exception:
        logger.exception("Error in snapshot cleanup worker")
        return False


# Create the worker class
AnalyticsWorker = create_worker_class(
    worker_functions=[
        generate_hourly_snapshot,
        generate_daily_snapshot,
        generate_weekly_snapshot,
        generate_monthly_snapshot,
        cleanup_old_snapshots,
    ],
    functions=[
        generate_hourly_snapshot,
        generate_daily_snapshot,
        generate_weekly_snapshot,
        generate_monthly_snapshot,
        cleanup_old_snapshots,
    ],
    max_jobs=2,  # Limited concurrent analytics processing
    job_timeout=300,  # 5 minutes per analytics task
)
