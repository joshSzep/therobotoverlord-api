"""Translation models for The Robot Overlord API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field

from therobotoverlord_api.database.models.base import BaseDBModel
from therobotoverlord_api.database.models.base import ContentType


class Translation(BaseDBModel):
    """Translation database model."""

    content_pk: UUID
    content_type: ContentType
    language_code: str = Field(max_length=10)
    original_content: str
    translated_content: str
    translation_quality_score: float | None = None
    translation_provider: str = "placeholder"
    translation_metadata: dict | None = None


class TranslationCreate(BaseModel):
    """Model for creating a new translation."""

    content_pk: UUID
    content_type: ContentType
    language_code: str = Field(max_length=10)
    original_content: str
    translated_content: str
    translation_quality_score: float | None = None
    translation_provider: str = "placeholder"
    translation_metadata: dict | None = None


class TranslationUpdate(BaseModel):
    """Model for updating a translation."""

    translated_content: str | None = None
    translation_quality_score: float | None = None
    translation_metadata: dict | None = None


class TranslationResponse(BaseModel):
    """Response model for translation API endpoints."""

    pk: UUID
    content_pk: UUID
    content_type: ContentType
    language_code: str
    original_content: str
    translated_content: str
    translation_quality_score: float | None
    translation_provider: str
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class ContentWithTranslation(BaseModel):
    """Model for content with its translation information."""

    content_pk: UUID
    content_type: ContentType
    english_content: str
    original_content: str | None = None
    source_language: str = "en"
    has_translation: bool = False
    translation_quality_score: float | None = None


class LanguageDetectionResult(BaseModel):
    """Result of language detection."""

    detected_language: str | None
    confidence: float | None
    is_english: bool


class TranslationRequest(BaseModel):
    """Request model for translation operations."""

    content: str
    source_language: str | None = None
    target_language: str = "en"


class TranslationResult(BaseModel):
    """Result of translation operation."""

    original_content: str
    translated_content: str
    source_language: str
    target_language: str
    quality_score: float | None = None
    provider: str
    metadata: dict | None = None
