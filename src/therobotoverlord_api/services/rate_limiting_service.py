"""Rate limiting service using Redis sliding window algorithm."""

import logging

from datetime import UTC
from datetime import datetime
from typing import Any

import redis.asyncio as redis

from therobotoverlord_api.config.rate_limiting import get_rate_limiting_settings

logger = logging.getLogger(__name__)


class RateLimitResult:
    """Result of a rate limit check."""

    def __init__(
        self,
        *,
        allowed: bool,
        limit: int,
        remaining: int,
        reset_time: datetime,
        retry_after: int | None = None,
    ):
        self.allowed = allowed
        self.limit = limit
        self.remaining = remaining
        self.reset_time = reset_time
        self.retry_after = retry_after


class RateLimitingService:
    """Redis-based rate limiting service using sliding window algorithm."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.settings = get_rate_limiting_settings()

    async def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window_seconds: int,
        key_suffix: str = "",
    ) -> RateLimitResult:
        """Check if request is within rate limit using sliding window.

        Args:
            identifier: Unique identifier (IP, user_id, etc.)
            limit: Maximum requests allowed in window
            window_seconds: Time window in seconds
            key_suffix: Optional suffix for the Redis key

        Returns:
            RateLimitResult with limit check details
        """
        if not self.settings.rate_limiting_enabled:
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit,
                reset_time=datetime.now(UTC),
            )

        # Check if IP is in bypass list
        if self._is_bypass_ip(identifier):
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit,
                reset_time=datetime.now(UTC),
            )

        key = f"{self.settings.rate_limit_key_prefix}{identifier}"
        if key_suffix:
            key = f"{key}:{key_suffix}"

        now = datetime.now(UTC)
        window_start = now.timestamp() - window_seconds

        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis.pipeline()

            # Remove expired entries
            pipe.zremrangebyscore(key, 0, window_start)

            # Count current requests in window
            pipe.zcard(key)

            # Add current request
            pipe.zadd(key, {str(now.timestamp()): now.timestamp()})

            # Set expiration
            pipe.expire(key, window_seconds)

            results = await pipe.execute()
            current_count = results[1]

            # Calculate remaining and reset time
            remaining = max(0, limit - current_count - 1)
            reset_time = now.replace(second=0, microsecond=0).replace(
                minute=now.minute + 1 if window_seconds == 60 else now.minute
            )

            if current_count >= limit:
                # Remove the request we just added since it's over limit
                await self.redis.zrem(key, str(now.timestamp()))

                retry_after = window_seconds
                return RateLimitResult(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_time=reset_time,
                    retry_after=retry_after,
                )

            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=remaining,
                reset_time=reset_time,
            )

        except Exception as e:
            logger.error(f"Rate limiting check failed: {e}")
            # Fail open - allow request if Redis is unavailable
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit,
                reset_time=datetime.now(UTC),
            )

    async def check_auth_rate_limit(
        self, ip_address: str, user_id: str | None = None
    ) -> RateLimitResult:
        """Check rate limit for authentication endpoints."""
        # Check IP-based limit first (stricter)
        ip_result = await self.check_rate_limit(
            identifier=ip_address,
            limit=self.settings.auth_requests_per_minute,
            window_seconds=60,
            key_suffix="auth_ip",
        )

        if not ip_result.allowed:
            return ip_result

        # Check user-based limit if user is identified
        if user_id:
            user_result = await self.check_rate_limit(
                identifier=user_id,
                limit=self.settings.auth_user_requests_per_minute,
                window_seconds=60,
                key_suffix="auth_user",
            )
            if not user_result.allowed:
                return user_result

        return ip_result

    async def check_admin_rate_limit(self, user_id: str) -> RateLimitResult:
        """Check rate limit for admin endpoints."""
        return await self.check_rate_limit(
            identifier=user_id,
            limit=self.settings.admin_requests_per_minute,
            window_seconds=60,
            key_suffix="admin",
        )

    async def check_rbac_rate_limit(self, user_id: str) -> RateLimitResult:
        """Check rate limit for RBAC endpoints."""
        return await self.check_rate_limit(
            identifier=user_id,
            limit=self.settings.rbac_requests_per_minute,
            window_seconds=60,
            key_suffix="rbac",
        )

    async def check_sanctions_rate_limit(self, user_id: str) -> RateLimitResult:
        """Check rate limit for sanctions endpoints."""
        return await self.check_rate_limit(
            identifier=user_id,
            limit=self.settings.sanctions_requests_per_minute,
            window_seconds=60,
            key_suffix="sanctions",
        )

    async def check_content_rate_limit(self, user_id: str) -> RateLimitResult:
        """Check rate limit for content creation endpoints."""
        return await self.check_rate_limit(
            identifier=user_id,
            limit=self.settings.content_requests_per_minute,
            window_seconds=60,
            key_suffix="content",
        )

    async def check_general_rate_limit(self, ip_address: str) -> RateLimitResult:
        """Check rate limit for general API endpoints."""
        return await self.check_rate_limit(
            identifier=ip_address,
            limit=self.settings.general_requests_per_minute,
            window_seconds=60,
            key_suffix="general",
        )

    def _is_bypass_ip(self, ip_address: str) -> bool:
        """Check if IP address should bypass rate limiting."""
        bypass_ips = [
            ip.strip()
            for ip in self.settings.rate_limit_bypass_ips.split(",")
            if ip.strip()
        ]
        return ip_address in bypass_ips

    async def get_rate_limit_info(
        self, identifier: str, key_suffix: str = ""
    ) -> dict[str, Any]:
        """Get current rate limit information for debugging."""
        key = f"{self.settings.rate_limit_key_prefix}{identifier}"
        if key_suffix:
            key = f"{key}:{key_suffix}"

        try:
            count = await self.redis.zcard(key)
            ttl = await self.redis.ttl(key)

            return {
                "key": key,
                "current_count": count,
                "ttl_seconds": ttl,
                "enabled": self.settings.rate_limiting_enabled,
            }
        except Exception as e:
            logger.error(f"Failed to get rate limit info: {e}")
            return {"error": str(e)}


# Service instance cache
_rate_limiting_service: RateLimitingService | None = None


async def get_rate_limiting_service() -> RateLimitingService:
    """Get rate limiting service instance."""
    global _rate_limiting_service  # noqa: PLW0603

    if _rate_limiting_service is None:
        try:
            # Import here to avoid circular imports
            from therobotoverlord_api.workers.redis_connection import get_redis_client

            redis_client = await get_redis_client()
            _rate_limiting_service = RateLimitingService(redis_client)
        except Exception as e:
            logger.error(f"Failed to initialize rate limiting service: {e}")
            # Return a mock service that allows all requests
            _rate_limiting_service = _create_mock_rate_limiting_service()

    return _rate_limiting_service


def _create_mock_rate_limiting_service() -> RateLimitingService:
    """Create a mock rate limiting service that allows all requests."""

    class MockRedis:
        async def pipeline(self):
            return MockPipeline()

        async def close(self):
            pass

    class MockPipeline:
        def zremrangebyscore(self, *args, **kwargs):
            return self

        def zadd(self, *args, **kwargs):
            return self

        def zcard(self, *args, **kwargs):
            return self

        def expire(self, *args, **kwargs):
            return self

        async def execute(self):
            return [0, 1, 0, True]  # Mock results that indicate success

    mock_redis = MockRedis()
    return RateLimitingService(mock_redis)  # type: ignore[reportGeneralTypeIssues, arg-type]
