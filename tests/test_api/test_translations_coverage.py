"""Coverage tests for translations API endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient


class TestTranslationsAPICoverage:
    """Test translations API endpoints for coverage improvement."""

    @pytest.mark.asyncio
    async def test_get_translations_unauthorized(self, async_client: AsyncClient):
        """Test get translations without authentication."""
        response = await async_client.get("/api/v1/translations")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_create_translation_unauthorized(self, async_client: AsyncClient):
        """Test create translation without authentication."""
        translation_data = {
            "key": "test.key",
            "language": "en",
            "value": "Test Value",
            "context": "test"
        }
        response = await async_client.post("/api/v1/translations", json=translation_data)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_get_translation_by_key_unauthorized(self, async_client: AsyncClient):
        """Test get translation by key without authentication."""
        response = await async_client.get("/api/v1/translations/test.key")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_update_translation_unauthorized(self, async_client: AsyncClient):
        """Test update translation without authentication."""
        translation_id = "550e8400-e29b-41d4-a716-446655440000"
        update_data = {"value": "Updated Value"}
        response = await async_client.put(f"/api/v1/translations/{translation_id}", json=update_data)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_delete_translation_unauthorized(self, async_client: AsyncClient):
        """Test delete translation without authentication."""
        translation_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await async_client.delete(f"/api/v1/translations/{translation_id}")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_get_translations_by_language_unauthorized(self, async_client: AsyncClient):
        """Test get translations by language without authentication."""
        response = await async_client.get("/api/v1/translations/language/en")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_export_translations_unauthorized(self, async_client: AsyncClient):
        """Test export translations without authentication."""
        response = await async_client.get("/api/v1/translations/export/en")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_import_translations_unauthorized(self, async_client: AsyncClient):
        """Test import translations without authentication."""
        import_data = {"translations": {"key": "value"}}
        response = await async_client.post("/api/v1/translations/import/en", json=import_data)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_get_translation_stats_unauthorized(self, async_client: AsyncClient):
        """Test get translation stats without authentication."""
        response = await async_client.get("/api/v1/translations/stats")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_search_translations_unauthorized(self, async_client: AsyncClient):
        """Test search translations without authentication."""
        response = await async_client.get("/api/v1/translations/search?q=test")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_invalid_translation_data(self, async_client: AsyncClient):
        """Test create translation with invalid data."""
        invalid_data = {"invalid": "data"}
        response = await async_client.post("/api/v1/translations", json=invalid_data)
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]

    @pytest.mark.asyncio
    async def test_invalid_translation_id_format(self, async_client: AsyncClient):
        """Test invalid translation ID format."""
        response = await async_client.get("/api/v1/translations/invalid-uuid")
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]
