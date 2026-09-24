"""Bounded multipart inference; persistence and uploads remain independent."""
from typing import Annotated
from fastapi import APIRouter, File, UploadFile, HTTPException
from . import config
from .image_classifier import normalize_image, get_classifier, aggregate, UNAVAILABLE
from .diagnostics import log_failure

router = APIRouter(prefix='/api/ai', tags=['Image suggestions'])

@router.post('/classify-contamination')
def classify_contamination(images: Annotated[list[UploadFile], File(alias='images[]')]):
    if not images or len(images) > config.MAX_IMAGES_PER_REPORT:
        raise HTTPException(422, f'Choose between 1 and {config.MAX_IMAGES_PER_REPORT} images.')
    normalized = []
    total = 0
    for image in images:
        data = image.file.read(config.MAX_IMAGE_BYTES + 1)
        total += len(data)
        if len(data) > config.MAX_IMAGE_BYTES or total > config.AI_MAX_BATCH_BYTES:
            raise HTTPException(413, f'Send images separately when their combined size exceeds {config.AI_MAX_BATCH_BYTES // (1024 * 1024)} MB.')
        normalized.append(normalize_image(data))
    classifier = get_classifier()
    if classifier is not None:
        try:
            results = classifier.classify(normalized)
            if len(results) != len(images):
                raise ValueError('Incomplete classification')
            suggestion = aggregate(results)
            return {'success': True, **suggestion, 'threshold': config.AI_CONFIDENCE_THRESHOLD,
                    'auto_select': suggestion['confidence'] >= config.AI_CONFIDENCE_THRESHOLD and suggestion['suggested_category'] != 'Other / Unclear',
                    'image_results': [result.model_dump() for result in results]}
        except Exception as exc:
            log_failure('Image inference unavailable; manual selection remains available', exc)
    return {'success': False, 'available': False, 'message': UNAVAILABLE, 'image_results': [],
            'suggested_category': None, 'confidence': None, 'threshold': config.AI_CONFIDENCE_THRESHOLD}
