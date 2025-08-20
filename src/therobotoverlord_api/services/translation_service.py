"""Translation service for The Robot Overlord API."""

import logging

from uuid import UUID

from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.models.translation import ContentWithTranslation
from therobotoverlord_api.database.models.translation import LanguageDetectionResult
from therobotoverlord_api.database.models.translation import Translation
from therobotoverlord_api.database.models.translation import TranslationCreate
from therobotoverlord_api.database.models.translation import TranslationResult
from therobotoverlord_api.database.models.translation import TranslationUpdate
from therobotoverlord_api.database.repositories.translation import TranslationRepository

logger = logging.getLogger(__name__)


class TranslationService:
    """Service for handling content translation operations."""

    def __init__(self):
        self.translation_repo = TranslationRepository()

    async def detect_language(self, content: str) -> LanguageDetectionResult:
        """
        Detect the language of content.

        Placeholder implementation - replace with actual language detection.
        """
        # Placeholder: Simple heuristic detection
        # TODO(josh): Replace with actual language detection service (e.g., langdetect, Google Translate API)

        # Simple check for common non-English patterns
        non_english_indicators = [
            "ñ",
            "ç",
            "ü",
            "ö",
            "ä",
            "é",
            "è",
            "à",
            "ù",
            "ì",
            "ò",  # European
            "ж",
            "ш",
            "щ",
            "ч",
            "ц",
            "\u0445",  # Cyrillic small letter ha
            "ф",
            "т",
            "\u0441",  # Cyrillic small letter es
            "\u0440",  # Cyrillic small letter er
            "的",
            "是",
            "在",
            "了",
            "和",
            "有",
            "我",
            "你",
            "他",
            "她",  # Chinese
            "の",
            "は",
            "が",
            "を",
            "に",
            "で",
            "と",
            "も",
            "から",
            "まで",  # Japanese
        ]

        has_non_english = any(
            char in content.lower() for char in non_english_indicators
        )

        if has_non_english:
            # Placeholder: Return a detected language
            detected_lang = "es"  # Default to Spanish for demo
            confidence = 0.8
        else:
            detected_lang = None
            confidence = 0.9

        return LanguageDetectionResult(
            detected_language=detected_lang,
            confidence=confidence,
            is_english=not has_non_english,
        )

    async def translate_to_english(
        self, content: str, source_language: str | None = None
    ) -> TranslationResult:
        """
        Translate content to English.

        Placeholder implementation - replace with actual translation service.
        """
        # Placeholder: Mock translation
        # TODO(josh): Replace with actual translation service (e.g., OpenAI, Google Translate)

        if not source_language:
            detection = await self.detect_language(content)
            source_language = detection.detected_language or "en"

        if source_language == "en":
            # Already English
            return TranslationResult(
                original_content=content,
                translated_content=content,
                source_language="en",
                target_language="en",
                quality_score=1.0,
                provider="none",
                metadata={"reason": "already_english"},
            )

        # Placeholder translation
        translated_content = f"[TRANSLATED FROM {source_language.upper()}] {content}"

        return TranslationResult(
            original_content=content,
            translated_content=translated_content,
            source_language=source_language,
            target_language="en",
            quality_score=0.85,  # Mock quality score
            provider="placeholder",
            metadata={
                "source_language": source_language,
                "method": "placeholder_translation",
            },
        )

    async def process_content_for_translation(
        self, content_pk: UUID | None, content_type: ContentType, content: str
    ) -> str:
        """
        Process content for translation and return the canonical English version.

        This is the main entry point for content translation during ingestion.
        """
        # Skip lookup if content_pk is None (during initial creation)
        if content_pk is None:
            # Process content directly for initial creation
            detection = await self.detect_language(content)
            if detection.is_english:
                return content
            translation_result = await self.translate_to_english(
                content, detection.detected_language
            )
            return translation_result.translated_content

        # Check if we already have a translation for this content
        existing_translation = await self.translation_repo.get_by_content(
            content_pk, content_type
        )

        if existing_translation:
            logger.info(
                f"Using existing translation for {content_type.value} {content_pk}"
            )
            return existing_translation.translated_content

        # Detect language
        detection = await self.detect_language(content)

        if detection.is_english:
            logger.info(f"Content {content_pk} is already in English")
            return content

        # Translate to English
        translation_result = await self.translate_to_english(
            content, detection.detected_language
        )

        # Store the translation
        translation_create = TranslationCreate(
            content_pk=content_pk,
            content_type=content_type,
            language_code=translation_result.source_language,
            original_content=translation_result.original_content,
            translated_content=translation_result.translated_content,
            translation_quality_score=translation_result.quality_score,
            translation_provider=translation_result.provider,
            translation_metadata=translation_result.metadata,
        )

        await self.translation_repo.create(translation_create)

        logger.info(
            f"Created translation for {content_type.value} {content_pk} "
            f"from {translation_result.source_language} to English"
        )

        return translation_result.translated_content

    async def get_content_with_translation(
        self, content_pk: UUID, content_type: ContentType, english_content: str
    ) -> ContentWithTranslation:
        """Get content with its translation information for appeals/display."""
        translation = await self.translation_repo.get_by_content(
            content_pk, content_type
        )

        if translation:
            return ContentWithTranslation(
                content_pk=content_pk,
                content_type=content_type,
                english_content=english_content,
                original_content=translation.original_content,
                source_language=translation.language_code,
                has_translation=True,
                translation_quality_score=translation.translation_quality_score,
            )

        return ContentWithTranslation(
            content_pk=content_pk,
            content_type=content_type,
            english_content=english_content,
            original_content=None,
            source_language="en",
            has_translation=False,
            translation_quality_score=None,
        )

    async def retranslate_content(
        self, content_pk: UUID, content_type: ContentType
    ) -> Translation | None:
        """Retranslate existing content (useful for quality improvements)."""
        existing_translation = await self.translation_repo.get_by_content(
            content_pk, content_type
        )

        if not existing_translation:
            logger.warning(
                f"No existing translation found for {content_type.value} {content_pk}"
            )
            return None

        # Retranslate
        translation_result = await self.translate_to_english(
            existing_translation.original_content, existing_translation.language_code
        )

        # Update the existing translation
        update_data = TranslationUpdate(
            translated_content=translation_result.translated_content,
            translation_quality_score=translation_result.quality_score,
            translation_metadata=translation_result.metadata,
        )

        updated_translation = await self.translation_repo.update(
            existing_translation.pk, update_data
        )

        logger.info(f"Retranslated {content_type.value} {content_pk}")
        return updated_translation

    async def get_translation_stats(self) -> dict:
        """Get translation service statistics."""
        return await self.translation_repo.get_translation_stats()

    async def get_language_distribution(self) -> list[dict]:
        """Get distribution of translations by language."""
        return await self.translation_repo.get_language_distribution()


async def get_translation_service() -> TranslationService:
    """Get the translation service instance."""
    return TranslationService()
