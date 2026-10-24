"""Validate original clinic image uploads independently of model inference."""

import io
import re
import warnings
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
MAX_IMAGE_DIMENSION = 8192
IMAGE_FORMATS = {
    "JPEG": ("image/jpeg", ".jpg"),
    "PNG": ("image/png", ".png"),
    "WEBP": ("image/webp", ".webp"),
}


def validate_image(content, declared_type, filename):
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=422, detail="Each image must contain 1 byte to 10 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                if image.format not in IMAGE_FORMATS:
                    raise ValueError("unsupported image format")
                width, height = image.size
                if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION or width * height > MAX_IMAGE_PIXELS:
                    raise ValueError("image dimensions exceed the limit")
                actual_type, extension = IMAGE_FORMATS[image.format]
                if declared_type != actual_type:
                    raise ValueError("image type does not match the file")
                if getattr(image, "n_frames", 1) != 1:
                    raise ValueError("animated images are not supported")
                image.verify()
            # verify() checks the container; load() also rejects truncated pixel data.
            with Image.open(io.BytesIO(content)) as image:
                image.load()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
            Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise HTTPException(
            status_code=422,
            detail="Upload valid, non-animated JPEG, PNG or WebP images (up to 8192 px per side and 20 megapixels).",
        )
    safe_name = Path((filename or "wound-image").replace("\\", "/")).name
    safe_name = re.sub(r"[\x00-\x1f\x7f]", "", safe_name).strip(" .")[:120] or "wound-image" + extension
    return actual_type, extension, safe_name
