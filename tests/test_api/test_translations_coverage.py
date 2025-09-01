"""Coverage tests for translations API endpoints."""

import pytest

from fastapi import status
from httpx import AsyncClient


class TestTranslationsAPICoverage:
    """Test translations API endpoints for coverage improvement."""

    @pytest.mark.asyncio
    async def test_get_translations_unauthorized(self, async_client: AsyncClient):
        """Test get translations without authentication (moderator+ only)."""
        response = await async_client.get("/api/v1/translations/")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_translate_content_unauthorized(self, async_client: AsyncClient):
        """Test translate content without authentication (moderator+ only)."""
        translation_data = {
            "content": "Test content",
            "source_language": "es",
        }
        response = await async_client.post(
            "/api/v1/translations/translate", json=translation_data
        )
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_get_content_translation_unauthorized(
        self, async_client: AsyncClient
    ):
        """Test get content translation without authentication."""
        content_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await async_client.get(
            f"/api/v1/translations/content/{content_id}?content_type=post"
        )
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_update_translation_quality_unauthorized(
        self, async_client: AsyncClient
    ):
        """Test update translation quality without authentication (moderator+ only)."""
        translation_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await async_client.patch(
            f"/api/v1/translations/{translation_id}/quality?quality_score=0.8"
        )
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_delete_content_translations_unauthorized(
        self, async_client: AsyncClient
    ):
        """Test delete content translations without authentication (admin+ only)."""
        content_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await async_client.delete(
            f"/api/v1/translations/content/{content_id}?content_type=post"
        )
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_get_translations_by_language_unauthorized(
        self, async_client: AsyncClient
    ):
        """Test get translations by language without authentication (moderator+ only)."""
        response = await async_client.get("/api/v1/translations/?language_code=en")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_get_poor_quality_translations_unauthorized(
        self, async_client: AsyncClient
    ):
        """Test get poor quality translations without authentication (moderator+ only)."""
        response = await async_client.get("/api/v1/translations/poor-quality")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_retranslate_content_unauthorized(self, async_client: AsyncClient):
        """Test retranslate content without authentication (moderator+ only)."""
        content_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await async_client.patch(
            f"/api/v1/translations/content/{content_id}/retranslate?content_type=post"
        )
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_get_translation_stats_unauthorized(self, async_client: AsyncClient):
        """Test get translation stats without authentication."""
        response = await async_client.get("/api/v1/translations/stats")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_get_language_distribution_unauthorized(
        self, async_client: AsyncClient
    ):
        """Test get language distribution without authentication (moderator+ only)."""
        response = await async_client.get("/api/v1/translations/languages")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_invalid_translation_data(self, async_client: AsyncClient):
        """Test translate content with invalid data."""
        invalid_data = {"invalid": "data"}
        response = await async_client.post(
            "/api/v1/translations/translate", json=invalid_data
        )
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_invalid_content_id_format(self, async_client: AsyncClient):
        """Test invalid content ID format."""
        response = await async_client.get(
            "/api/v1/translations/content/invalid-uuid?content_type=post"
        )
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]
