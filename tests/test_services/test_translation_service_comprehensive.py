"""Comprehensive tests for TranslationService."""

import pytest
from datetime import datetime
from datetime import UTC
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.models.translation import ContentWithTranslation
from therobotoverlord_api.database.models.translation import LanguageDetectionResult
from therobotoverlord_api.database.models.translation import Translation
from therobotoverlord_api.database.models.translation import TranslationCreate
from therobotoverlord_api.database.models.translation import TranslationResult
from therobotoverlord_api.database.models.translation import TranslationUpdate
from therobotoverlord_api.services.translation_service import TranslationService


class TestTranslationService:
    """Test class for TranslationService."""

    @pytest.fixture
    def service(self):
        """Create TranslationService instance."""
        return TranslationService()

    @pytest.fixture
    def mock_translation(self):
        """Mock Translation instance."""
        return Translation(
            pk=uuid4(),
            content_pk=uuid4(),
            content_type=ContentType.POST,
            language_code="es",
            original_content="Hola mundo",
            translated_content="Hello world",
            translation_quality_score=0.95,
            translation_provider="test_provider",
            translation_metadata={"confidence": 0.95},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )

    @pytest.mark.asyncio
    async def test_detect_language_english_content(self, service):
        """Test language detection for English content."""
        english_content = "This is a test message in English."

        result = await service.detect_language(english_content)

        assert isinstance(result, LanguageDetectionResult)
        assert result.is_english is True
        assert result.detected_language is None
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_detect_language_spanish_content(self, service):
        """Test language detection for Spanish content."""
        spanish_content = "Hola, niño. Mañana será un día especial."

        result = await service.detect_language(spanish_content)

        assert isinstance(result, LanguageDetectionResult)
        assert result.is_english is False
        assert result.detected_language == "es"
        assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_detect_language_chinese_content(self, service):
        """Test language detection for Chinese content."""
        chinese_content = "你好世界，这是一个测试消息。"

        result = await service.detect_language(chinese_content)

        assert isinstance(result, LanguageDetectionResult)
        assert result.is_english is False
        assert result.detected_language == "es"  # Placeholder returns Spanish
        assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_detect_language_cyrillic_content(self, service):
        """Test language detection for Cyrillic content."""
        cyrillic_content = "Привет мир, это тестовое сообщение."

        result = await service.detect_language(cyrillic_content)

        assert isinstance(result, LanguageDetectionResult)
        assert result.is_english is False
        assert result.detected_language == "es"  # Placeholder returns Spanish
        assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_detect_language_mixed_content(self, service):
        """Test language detection for mixed content."""
        mixed_content = "Hello world, niño está today?"

        result = await service.detect_language(mixed_content)

        assert isinstance(result, LanguageDetectionResult)
        assert result.is_english is False
        assert result.detected_language == "es"
        assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_translate_to_english_already_english(self, service):
        """Test translation when content is already in English."""
        english_content = "This is already in English."

        result = await service.translate_to_english(english_content, "en")

        assert isinstance(result, TranslationResult)
        assert result.original_content == english_content
        assert result.translated_content == english_content
        assert result.source_language == "en"
        assert result.target_language == "en"
        assert result.quality_score == 1.0
        assert result.provider == "none"
        assert result.metadata == {"reason": "already_english"}

    @pytest.mark.asyncio
    async def test_translate_to_english_from_spanish(self, service):
        """Test translation from Spanish to English."""
        spanish_content = "Hola mundo"
        source_language = "es"

        result = await service.translate_to_english(spanish_content, source_language)

        assert isinstance(result, TranslationResult)
        assert result.original_content == spanish_content
        assert result.translated_content == "[TRANSLATED FROM ES] Hola mundo"
        assert result.source_language == "es"
        assert result.target_language == "en"
        assert result.quality_score == 0.85
        assert result.provider == "placeholder"
        assert result.metadata == {
            "source_language": "es",
            "method": "placeholder_translation"
        }

    @pytest.mark.asyncio
    async def test_translate_to_english_auto_detect(self, service):
        """Test translation with automatic language detection."""
        spanish_content = "Hola, ¿cómo estás?"

        with patch.object(service, "detect_language") as mock_detect:
            mock_detect.return_value = LanguageDetectionResult(
                detected_language="es", confidence=0.9, is_english=False
            )

            result = await service.translate_to_english(spanish_content)

            mock_detect.assert_called_once_with(spanish_content)
            assert result.source_language == "es"
            assert result.translated_content == "[TRANSLATED FROM ES] Hola, ¿cómo estás?"

    @pytest.mark.asyncio
    async def test_translate_to_english_auto_detect_english(self, service):
        """Test translation with auto-detection returning English."""
        english_content = "Hello world"

        with patch.object(service, "detect_language") as mock_detect:
            mock_detect.return_value = LanguageDetectionResult(
                detected_language=None, confidence=0.9, is_english=True
            )

            result = await service.translate_to_english(english_content)

            mock_detect.assert_called_once_with(english_content)
            assert result.source_language == "en"
            assert result.translated_content == english_content

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.translation_service.TranslationRepository")
    async def test_process_content_for_translation_no_content_pk(self, mock_repo, service):
        """Test processing content without content_pk (initial creation)."""
        content = "Hola mundo"
        content_type = ContentType.POST

        with patch.object(service, "detect_language") as mock_detect, \
             patch.object(service, "translate_to_english") as mock_translate:

            mock_detect.return_value = LanguageDetectionResult(
                detected_language="es", confidence=0.9, is_english=False
            )
            mock_translate.return_value = TranslationResult(
                original_content=content,
                translated_content="Hello world",
                source_language="es",
                target_language="en",
                quality_score=0.9,
                provider="test",
                metadata={}
            )

            result = await service.process_content_for_translation(None, content_type, content)

            mock_detect.assert_called_once_with(content)
            mock_translate.assert_called_once_with(content, "es")
            assert result == "Hello world"

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.translation_service.TranslationRepository")
    async def test_process_content_for_translation_english_no_pk(self, mock_repo, service):
        """Test processing English content without content_pk."""
        content = "Hello world"
        content_type = ContentType.POST

        with patch.object(service, "detect_language") as mock_detect:
            mock_detect.return_value = LanguageDetectionResult(
                detected_language=None, confidence=0.9, is_english=True
            )

            result = await service.process_content_for_translation(None, content_type, content)

            mock_detect.assert_called_once_with(content)
            assert result == content

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.translation_service.TranslationRepository")
    async def test_process_content_existing_translation(self, mock_repo, service, mock_translation):
        """Test processing content with existing translation."""
        content_pk = uuid4()
        content = "Hola mundo"
        content_type = ContentType.POST

        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_content.return_value = mock_translation
        mock_repo.return_value = mock_repo_instance
        service.translation_repo = mock_repo_instance

        result = await service.process_content_for_translation(content_pk, content_type, content)

        mock_repo_instance.get_by_content.assert_called_once_with(content_pk, content_type)
        assert result == mock_translation.translated_content

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.translation_service.TranslationRepository")
    async def test_process_content_english_existing_pk(self, mock_repo, service):
        """Test processing English content with existing content_pk."""
        content_pk = uuid4()
        content = "Hello world"
        content_type = ContentType.POST

        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_content.return_value = None
        mock_repo.return_value = mock_repo_instance
        service.translation_repo = mock_repo_instance

        with patch.object(service, "detect_language") as mock_detect:
            mock_detect.return_value = LanguageDetectionResult(
                detected_language=None, confidence=0.9, is_english=True
            )

            result = await service.process_content_for_translation(content_pk, content_type, content)

            mock_repo_instance.get_by_content.assert_called_once_with(content_pk, content_type)
            mock_detect.assert_called_once_with(content)
            assert result == content

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.translation_service.TranslationRepository")
    async def test_process_content_new_translation(self, mock_repo, service):
        """Test processing content that needs new translation."""
        content_pk = uuid4()
        content = "Hola mundo"
        content_type = ContentType.POST

        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_content.return_value = None
        mock_repo_instance.create.return_value = None
        mock_repo.return_value = mock_repo_instance
        service.translation_repo = mock_repo_instance

        with patch.object(service, "detect_language") as mock_detect, \
             patch.object(service, "translate_to_english") as mock_translate:

            mock_detect.return_value = LanguageDetectionResult(
                detected_language="es", confidence=0.9, is_english=False
            )
            mock_translate.return_value = TranslationResult(
                original_content=content,
                translated_content="Hello world",
                source_language="es",
                target_language="en",
                quality_score=0.9,
                provider="test",
                metadata={"test": "data"}
            )

            result = await service.process_content_for_translation(content_pk, content_type, content)

            mock_repo_instance.get_by_content.assert_called_once_with(content_pk, content_type)
            mock_detect.assert_called_once_with(content)
            mock_translate.assert_called_once_with(content, "es")
            mock_repo_instance.create.assert_called_once()
            
            # Verify the TranslationCreate object passed to create
            create_call_args = mock_repo_instance.create.call_args[0][0]
            assert isinstance(create_call_args, TranslationCreate)
            assert create_call_args.content_pk == content_pk
            assert create_call_args.content_type == content_type
            assert create_call_args.language_code == "es"
            assert create_call_args.original_content == content
            assert create_call_args.translated_content == "Hello world"
            
            assert result == "Hello world"

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.translation_service.TranslationRepository")
    async def test_get_content_with_translation_exists(self, mock_repo, service, mock_translation):
        """Test getting content with existing translation."""
        content_pk = uuid4()
        content_type = ContentType.POST
        english_content = "Hello world"

        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_content.return_value = mock_translation
        mock_repo.return_value = mock_repo_instance
        service.translation_repo = mock_repo_instance

        result = await service.get_content_with_translation(content_pk, content_type, english_content)

        mock_repo_instance.get_by_content.assert_called_once_with(content_pk, content_type)
        assert isinstance(result, ContentWithTranslation)
        assert result.content_pk == content_pk
        assert result.content_type == content_type
        assert result.english_content == english_content
        assert result.original_content == mock_translation.original_content
        assert result.source_language == mock_translation.language_code
        assert result.has_translation is True
        assert result.translation_quality_score == mock_translation.translation_quality_score

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.translation_service.TranslationRepository")
    async def test_get_content_with_translation_no_translation(self, mock_repo, service):
        """Test getting content without existing translation."""
        content_pk = uuid4()
        content_type = ContentType.POST
        english_content = "Hello world"

        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_content.return_value = None
        mock_repo.return_value = mock_repo_instance
        service.translation_repo = mock_repo_instance

        result = await service.get_content_with_translation(content_pk, content_type, english_content)

        mock_repo_instance.get_by_content.assert_called_once_with(content_pk, content_type)
        assert isinstance(result, ContentWithTranslation)
        assert result.content_pk == content_pk
        assert result.content_type == content_type
        assert result.english_content == english_content
        assert result.original_content is None
        assert result.source_language == "en"
        assert result.has_translation is False
        assert result.translation_quality_score is None

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.translation_service.TranslationRepository")
    async def test_retranslate_content_success(self, mock_repo, service, mock_translation):
        """Test retranslating existing content successfully."""
        content_pk = uuid4()
        content_type = ContentType.POST
        updated_translation = Translation(
            pk=mock_translation.pk,
            content_pk=content_pk,
            content_type=content_type,
            language_code="es",
            original_content="Hola mundo",
            translated_content="Hello world (updated)",
            translation_quality_score=0.98,
            translation_provider="updated_provider",
            translation_metadata={"updated": True},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )

        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_content.return_value = mock_translation
        mock_repo_instance.update.return_value = updated_translation
        mock_repo.return_value = mock_repo_instance
        service.translation_repo = mock_repo_instance

        with patch.object(service, "translate_to_english") as mock_translate:
            mock_translate.return_value = TranslationResult(
                original_content="Hola mundo",
                translated_content="Hello world (updated)",
                source_language="es",
                target_language="en",
                quality_score=0.98,
                provider="updated_provider",
                metadata={"updated": True}
            )

            result = await service.retranslate_content(content_pk, content_type)

            mock_repo_instance.get_by_content.assert_called_once_with(content_pk, content_type)
            mock_translate.assert_called_once_with(
                mock_translation.original_content, mock_translation.language_code
            )
            mock_repo_instance.update.assert_called_once()
            
            # Verify the update data
            update_call_args = mock_repo_instance.update.call_args[0]
            assert update_call_args[0] == mock_translation.pk
            update_data = update_call_args[1]
            assert isinstance(update_data, TranslationUpdate)
            assert update_data.translated_content == "Hello world (updated)"
            assert update_data.translation_quality_score == 0.98
            
            assert result == updated_translation

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.translation_service.TranslationRepository")
    async def test_retranslate_content_not_found(self, mock_repo, service):
        """Test retranslating content that doesn't exist."""
        content_pk = uuid4()
        content_type = ContentType.POST

        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_content.return_value = None
        mock_repo.return_value = mock_repo_instance
        service.translation_repo = mock_repo_instance

        result = await service.retranslate_content(content_pk, content_type)

        mock_repo_instance.get_by_content.assert_called_once_with(content_pk, content_type)
        assert result is None

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.translation_service.TranslationRepository")
    async def test_get_translation_stats(self, mock_repo, service):
        """Test getting translation statistics."""
        mock_stats = {
            "total_translations": 150,
            "languages_count": 12,
            "avg_quality_score": 0.87
        }

        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_translation_stats.return_value = mock_stats
        mock_repo.return_value = mock_repo_instance
        service.translation_repo = mock_repo_instance

        result = await service.get_translation_stats()

        mock_repo_instance.get_translation_stats.assert_called_once()
        assert result == mock_stats

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.translation_service.TranslationRepository")
    async def test_get_language_distribution(self, mock_repo, service):
        """Test getting language distribution."""
        mock_distribution = [
            {"language_code": "es", "count": 45},
            {"language_code": "fr", "count": 32},
            {"language_code": "de", "count": 28}
        ]

        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_language_distribution.return_value = mock_distribution
        mock_repo.return_value = mock_repo_instance
        service.translation_repo = mock_repo_instance

        result = await service.get_language_distribution()

        mock_repo_instance.get_language_distribution.assert_called_once()
        assert result == mock_distribution

    @pytest.mark.asyncio
    async def test_get_translation_service_function(self):
        """Test the get_translation_service factory function."""
        from therobotoverlord_api.services.translation_service import get_translation_service
        
        service = await get_translation_service()
        
        assert isinstance(service, TranslationService)
        assert hasattr(service, "translation_repo")

    @pytest.mark.asyncio
    async def test_detect_language_empty_content(self, service):
        """Test language detection with empty content."""
        result = await service.detect_language("")

        assert isinstance(result, LanguageDetectionResult)
        assert result.is_english is True
        assert result.detected_language is None
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_detect_language_japanese_content(self, service):
        """Test language detection for Japanese content."""
        japanese_content = "こんにちは世界、これはテストメッセージです。"

        result = await service.detect_language(japanese_content)

        assert isinstance(result, LanguageDetectionResult)
        assert result.is_english is False
        assert result.detected_language == "es"  # Placeholder returns Spanish
        assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_detect_language_european_accents(self, service):
        """Test language detection for European languages with accents."""
        french_content = "Bonjour, comment allez-vous? J'espère que vous passez une bonne journée."

        result = await service.detect_language(french_content)

        assert isinstance(result, LanguageDetectionResult)
        assert result.is_english is False
        assert result.detected_language == "es"
        assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_translate_to_english_unknown_language(self, service):
        """Test translation from unknown/unspecified language."""
        content = "Some content"

        with patch.object(service, "detect_language") as mock_detect:
            mock_detect.return_value = LanguageDetectionResult(
                detected_language=None, confidence=0.5, is_english=True
            )

            result = await service.translate_to_english(content, None)

            mock_detect.assert_called_once_with(content)
            assert result.source_language == "en"
            assert result.translated_content == content

    @pytest.mark.asyncio
    async def test_translate_to_english_detected_unknown(self, service):
        """Test translation when detection returns unknown language."""
        content = "Some content"

        with patch.object(service, "detect_language") as mock_detect:
            mock_detect.return_value = LanguageDetectionResult(
                detected_language=None, confidence=0.5, is_english=False
            )

            result = await service.translate_to_english(content, None)

            mock_detect.assert_called_once_with(content)
            assert result.source_language == "en"  # Defaults to "en" when None
            assert result.translated_content == content
