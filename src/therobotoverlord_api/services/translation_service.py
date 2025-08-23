"""Translation service for The Robot Overlord API."""

import logging

from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field

from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.models.translation import ContentWithTranslation
from therobotoverlord_api.database.models.translation import LanguageDetectionResult
from therobotoverlord_api.database.models.translation import Translation
from therobotoverlord_api.database.models.translation import TranslationCreate
from therobotoverlord_api.database.models.translation import TranslationResult
from therobotoverlord_api.database.models.translation import TranslationUpdate
from therobotoverlord_api.database.repositories.translation import TranslationRepository
from therobotoverlord_api.services.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class CombinedTranslationResponse(BaseModel):
    """Structured response for combined language detection and translation."""

    detected_language: str = Field(
        description="ISO 639-1 language code of the detected language (e.g., 'en', 'es', 'fr')"
    )
    confidence: float = Field(
        description="Confidence score for language detection (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    is_english: bool = Field(description="Whether the detected language is English")
    translation: str | None = Field(
        description="English translation of the text (None if already English)",
        default=None,
    )


class TranslationService:
    """Service for handling content translation operations."""

    SUPPORTED_LANGUAGES: ClassVar[set[str]] = {
        "en",
        "es",
        "fr",
        "de",
        "it",
        "pt",
        "ru",
        "zh",
        "ja",
        "ko",
        "ar",
        "hi",
    }

    def __init__(self):
        self.translation_repo = TranslationRepository()
        self.llm_client = None

    async def _get_llm_client(self):
        """Get LLM client instance."""
        if self.llm_client is None:
            self.llm_client = await get_llm_client()
        return self.llm_client

    async def detect_language_and_translate(
        self, content: str
    ) -> CombinedTranslationResponse:
        """
        Detect language and translate to English in a single LLM call for cost efficiency.
        """
        llm_client = await self._get_llm_client()

        prompt = f"""Analyze the following text and:
1. Detect its language (provide ISO 639-1 code like 'en', 'es', 'fr', 'de', 'zh', 'ja', etc.)
2. Determine your confidence in the detection (0.0 to 1.0)
3. Check if it's already in English
4. If not English, provide an accurate English translation

Text: {content[:1000]}"""  # Increased limit since we're doing both tasks

        try:
            response = await llm_client.run_translation_agent(
                prompt, output_type=CombinedTranslationResponse
            )

            # Validate the detected language is supported
            if response.detected_language not in self.SUPPORTED_LANGUAGES:
                logger.warning(
                    f"LLM detected unsupported language: {response.detected_language}"
                )
                # Fall back to heuristic detection
                fallback_result = await self._fallback_language_detection(content)
                return CombinedTranslationResponse(
                    detected_language=fallback_result.detected_language or "en",
                    confidence=fallback_result.confidence or 0.5,
                    is_english=fallback_result.is_english,
                    translation=None if fallback_result.is_english else content,
                )

            return response

        except Exception as e:
            logger.error(f"Error in combined LLM translation: {e}")
            # Fall back to heuristic detection
            fallback_result = await self._fallback_language_detection(content)
            return CombinedTranslationResponse(
                detected_language=fallback_result.detected_language or "en",
                confidence=fallback_result.confidence or 0.5,
                is_english=fallback_result.is_english,
                translation=None if fallback_result.is_english else content,
            )

    async def detect_language(self, content: str) -> LanguageDetectionResult:
        """
        Detect the language of content (legacy method for backward compatibility).
        Uses the combined approach internally.
        """
        combined_result = await self.detect_language_and_translate(content)
        return LanguageDetectionResult(
            detected_language=combined_result.detected_language,
            confidence=combined_result.confidence,
            is_english=combined_result.is_english,
        )

    async def _fallback_language_detection(
        self, content: str
    ) -> LanguageDetectionResult:
        """Fallback language detection using simple heuristics."""
        # Check for specific language patterns
        content_lower = content.lower()

        # Check for Spanish
        if any(
            indicator in content_lower
            for indicator in [
                "ñ",
                "¿",
                "¡",
                "mañana",
                "niño",
                "será",
                "día",
            ]
        ):
            return LanguageDetectionResult(
                detected_language="es",
                confidence=0.8,
                is_english=False,
            )

        # Check for French
        if any(char in content for char in "àâäéèêëîïôöùûüÿç"):
            return LanguageDetectionResult(
                detected_language="fr",
                confidence=0.8,
                is_english=False,
            )

        # Check for Chinese characters
        if any("\u4e00" <= char <= "\u9fff" for char in content):
            return LanguageDetectionResult(
                detected_language="zh",
                confidence=0.8,
                is_english=False,
            )

        # Check for Cyrillic characters
        if any("\u0400" <= char <= "\u04ff" for char in content):
            return LanguageDetectionResult(
                detected_language="ru",
                confidence=0.8,
                is_english=False,
            )

        # Check for Japanese characters
        if any("\u3040" <= char <= "\u30ff" for char in content):
            return LanguageDetectionResult(
                detected_language="ja",
                confidence=0.8,
                is_english=False,
            )

        # Check for Korean characters
        if any("\u1100" <= char <= "\u11ff" for char in content):
            return LanguageDetectionResult(
                detected_language="ko",
                confidence=0.8,
                is_english=False,
            )

        # Default to English if no non-English patterns found
        return LanguageDetectionResult(
            detected_language="en",
            confidence=0.9,
            is_english=True,
        )

    async def translate_to_english(
        self, content: str, source_language: str | None = None
    ) -> TranslationResult:
        """
        Translate content to English using the combined LLM approach for cost efficiency.
        """
        # Use the combined approach to get both detection and translation in one call
        combined_result = await self.detect_language_and_translate(content)

        if combined_result.is_english:
            # Already English
            return TranslationResult(
                original_content=content,
                translated_content=content,
                source_language=combined_result.detected_language,
                target_language="en",
                quality_score=combined_result.confidence,
                provider="llm",
                metadata={"reason": "already_english", "method": "combined_detection"},
            )

        # Use the translation from the combined result
        translated_content = combined_result.translation or content

        return TranslationResult(
            original_content=content,
            translated_content=translated_content,
            source_language=combined_result.detected_language,
            target_language="en",
            quality_score=combined_result.confidence,
            provider="llm",
            metadata={
                "source_language": combined_result.detected_language,
                "method": "combined_translation",
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
