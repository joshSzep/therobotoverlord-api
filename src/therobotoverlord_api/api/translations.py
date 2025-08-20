"""Translation API endpoints for The Robot Overlord."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status

from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.auth.dependencies import require_role
from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.translation import ContentWithTranslation
from therobotoverlord_api.database.models.translation import TranslationRequest
from therobotoverlord_api.database.models.translation import TranslationResponse
from therobotoverlord_api.database.models.translation import TranslationResult
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.database.repositories.translation import TranslationRepository
from therobotoverlord_api.services.translation_service import get_translation_service

router = APIRouter(prefix="/translations", tags=["translations"])

# Create dependency instances
moderator_dependency = require_role(UserRole.MODERATOR)


@router.get("/content/{content_id}")
async def get_content_translation(
    content_id: UUID,
    content_type: Annotated[ContentType, Query()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ContentWithTranslation:
    """Get translation information for a specific content item."""
    translation_repo = TranslationRepository()
    translation_service = await get_translation_service()

    # Get the translation if it exists
    translation = await translation_repo.get_by_content(content_id, content_type)

    if not translation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No translation found for this content",
        )

    # Return content with translation info
    return await translation_service.get_content_with_translation(
        content_id, content_type, translation.translated_content
    )


@router.get("/content/{content_id}/original")
async def get_original_content(
    content_id: UUID,
    content_type: Annotated[ContentType, Query()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get the original (untranslated) content for appeals or review."""
    translation_repo = TranslationRepository()

    translation = await translation_repo.get_by_content(content_id, content_type)

    if not translation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No original content found - content was submitted in English",
        )

    return {
        "content_id": content_id,
        "content_type": content_type,
        "original_content": translation.original_content,
        "source_language": translation.language_code,
        "translated_content": translation.translated_content,
        "quality_score": translation.translation_quality_score,
    }


@router.get("/")
async def get_translations(
    current_user: Annotated[User, Depends(moderator_dependency)],
    language_code: Annotated[str | None, Query(max_length=10)] = None,
    content_type: Annotated[ContentType | None, Query()] = None,
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TranslationResponse]:
    """Get translations with optional filtering (moderator+ only)."""
    translation_repo = TranslationRepository()

    if language_code:
        translations = await translation_repo.get_by_language(
            language_code, limit, offset
        )
    else:
        translations = await translation_repo.get_all(limit, offset)

    return [
        TranslationResponse.model_validate(translation.model_dump())
        for translation in translations
    ]


@router.get("/poor-quality")
async def get_poor_quality_translations(
    current_user: Annotated[User, Depends(moderator_dependency)],
    quality_threshold: Annotated[float, Query(ge=0.0, le=1.0)] = 0.7,
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TranslationResponse]:
    """Get translations with poor quality scores (moderator+ only)."""
    translation_repo = TranslationRepository()

    translations = await translation_repo.get_poor_quality_translations(
        quality_threshold, limit, offset
    )

    return [
        TranslationResponse.model_validate(translation.model_dump())
        for translation in translations
    ]


@router.post("/translate")
async def translate_content(
    translation_request: TranslationRequest,
    current_user: Annotated[User, Depends(moderator_dependency)],
) -> TranslationResult:
    """Translate content manually (moderator+ only, for testing/debugging)."""
    translation_service = await get_translation_service()

    return await translation_service.translate_to_english(
        translation_request.content, translation_request.source_language
    )


@router.patch("/content/{content_id}/retranslate")
async def retranslate_content(
    content_id: UUID,
    content_type: Annotated[ContentType, Query()],
    current_user: Annotated[User, Depends(moderator_dependency)],
) -> TranslationResponse:
    """Retranslate existing content (moderator+ only)."""
    translation_service = await get_translation_service()

    updated_translation = await translation_service.retranslate_content(
        content_id, content_type
    )

    if not updated_translation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No translation found to retranslate",
        )

    return TranslationResponse.model_validate(updated_translation.model_dump())


@router.patch("/{translation_id}/quality")
async def update_translation_quality(
    translation_id: UUID,
    current_user: Annotated[User, Depends(moderator_dependency)],
    quality_score: Annotated[float, Query(ge=0.0, le=1.0)],
) -> TranslationResponse:
    """Update translation quality score (moderator+ only)."""
    translation_repo = TranslationRepository()

    updated_translation = await translation_repo.update_quality_score(
        translation_id, quality_score, None
    )

    if not updated_translation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Translation not found"
        )

    return TranslationResponse.model_validate(updated_translation.model_dump())


@router.get("/stats")
async def get_translation_stats(
    current_user: Annotated[User, Depends(moderator_dependency)],
) -> dict:
    """Get translation service statistics (moderator+ only)."""
    translation_service = await get_translation_service()
    return await translation_service.get_translation_stats()


@router.get("/languages")
async def get_language_distribution(
    current_user: Annotated[User, Depends(moderator_dependency)],
) -> list[dict]:
    """Get distribution of translations by language (moderator+ only)."""
    translation_service = await get_translation_service()
    return await translation_service.get_language_distribution()


@router.delete("/content/{content_id}")
async def delete_content_translations(
    content_id: UUID,
    content_type: Annotated[ContentType, Query()],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
) -> dict:
    """Delete all translations for a content item (admin+ only)."""
    translation_repo = TranslationRepository()

    success = await translation_repo.delete_by_content(content_id, content_type)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No translations found for this content",
        )

    return {
        "message": "Translations deleted successfully",
        "content_id": content_id,
        "content_type": content_type,
    }
