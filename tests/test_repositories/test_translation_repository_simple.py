"""Simple tests for TranslationRepository to improve coverage."""

from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.repositories.translation import TranslationRepository


class TestTranslationRepositorySimple:
    """Simple test class for TranslationRepository."""

    @pytest.fixture
    def translation_repo(self):
        """Create a TranslationRepository instance."""
        return TranslationRepository()

    @pytest.fixture
    def mock_record(self):
        """Create a mock database record."""
        return {
            "pk": uuid4(),
            "content_pk": uuid4(),
            "content_type": "post",
            "language_code": "es",
            "original_content": "Hello world",
            "translated_content": "Hola mundo",
            "translation_quality_score": 0.95,
            "translation_provider": "google",
            "translation_metadata": {"confidence": 0.95},
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.translation.get_db_connection")
    async def test_get_by_content(self, mock_get_db, translation_repo, mock_record):
        """Test getting translation by content."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = mock_record
        
        content_pk = uuid4()
        result = await translation_repo.get_by_content(content_pk, ContentType.POST)
        
        mock_conn.fetchrow.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.translation.get_db_connection")
    async def test_get_by_content_not_found(self, mock_get_db, translation_repo):
        """Test getting translation by content when not found."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        
        content_pk = uuid4()
        result = await translation_repo.get_by_content(content_pk, ContentType.POST)
        
        mock_conn.fetchrow.assert_called_once()
        assert result is None

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.translation.get_db_connection")
    async def test_get_by_content_and_language(self, mock_get_db, translation_repo, mock_record):
        """Test getting translation by content and language."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = mock_record
        
        content_pk = uuid4()
        result = await translation_repo.get_by_content_and_language(
            content_pk, ContentType.POST, "es"
        )
        
        mock_conn.fetchrow.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.translation.get_db_connection")
    async def test_get_translations_for_content(self, mock_get_db, translation_repo, mock_record):
        """Test getting all translations for content."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [mock_record, mock_record]
        
        content_pk = uuid4()
        result = await translation_repo.get_translations_for_content(content_pk, ContentType.POST)
        
        mock_conn.fetch.assert_called_once()
        assert len(result) == 2

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.translation.get_db_connection")
    async def test_get_by_language(self, mock_get_db, translation_repo, mock_record):
        """Test getting translations by language."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [mock_record]
        
        result = await translation_repo.get_by_language("es", limit=10, offset=0)
        
        mock_conn.fetch.assert_called_once()
        assert len(result) == 1

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.translation.get_db_connection")
    async def test_get_poor_quality_translations(self, mock_get_db, translation_repo, mock_record):
        """Test getting poor quality translations."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [mock_record]
        
        result = await translation_repo.get_poor_quality_translations(
            quality_threshold=0.7, limit=10, offset=0
        )
        
        mock_conn.fetch.assert_called_once()
        assert len(result) == 1

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.translation.get_db_connection")
    async def test_update_quality_score(self, mock_get_db, translation_repo, mock_record):
        """Test updating quality score."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = mock_record
        
        translation_pk = uuid4()
        result = await translation_repo.update_quality_score(
            translation_pk, 0.85, {"updated": True}
        )
        
        mock_conn.fetchrow.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.translation.get_db_connection")
    async def test_delete_by_content_success(self, mock_get_db, translation_repo):
        """Test deleting translations by content."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn
        mock_conn.execute.return_value = "DELETE 2"
        
        content_pk = uuid4()
        result = await translation_repo.delete_by_content(content_pk, ContentType.POST)
        
        mock_conn.execute.assert_called_once()
        assert result is True

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.translation.get_db_connection")
    async def test_delete_by_content_no_rows(self, mock_get_db, translation_repo):
        """Test deleting translations by content when no rows affected."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn
        mock_conn.execute.return_value = "DELETE 0"
        
        content_pk = uuid4()
        result = await translation_repo.delete_by_content(content_pk, ContentType.POST)
        
        mock_conn.execute.assert_called_once()
        assert result is False

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.translation.get_db_connection")
    async def test_get_translation_stats(self, mock_get_db, translation_repo):
        """Test getting translation statistics."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn
        mock_stats = {
            "total_translations": 100,
            "unique_languages": 5,
            "translated_content_items": 80,
            "avg_quality_score": 0.85,
            "poor_quality_count": 10
        }
        mock_conn.fetchrow.return_value = mock_stats
        
        result = await translation_repo.get_translation_stats()
        
        mock_conn.fetchrow.assert_called_once()
        assert result == mock_stats

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.translation.get_db_connection")
    async def test_get_translation_stats_no_data(self, mock_get_db, translation_repo):
        """Test getting translation statistics when no data."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        
        result = await translation_repo.get_translation_stats()
        
        mock_conn.fetchrow.assert_called_once()
        assert result == {}

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.translation.get_db_connection")
    async def test_get_language_distribution(self, mock_get_db, translation_repo):
        """Test getting language distribution."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn
        mock_distribution = [
            {"language_code": "es", "translation_count": 50, "avg_quality_score": 0.9},
            {"language_code": "fr", "translation_count": 30, "avg_quality_score": 0.8}
        ]
        mock_conn.fetch.return_value = mock_distribution
        
        result = await translation_repo.get_language_distribution()
        
        mock_conn.fetch.assert_called_once()
        assert result == mock_distribution

    def test_record_to_model(self, translation_repo, mock_record):
        """Test converting record to model."""
        result = translation_repo._record_to_model(mock_record)
        
        assert result.pk == mock_record["pk"]
        assert result.content_pk == mock_record["content_pk"]
        assert result.language_code == mock_record["language_code"]
