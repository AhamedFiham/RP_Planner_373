"""Shared upload validation. Images are decoded in memory and never saved."""
from io import BytesIO
from pathlib import Path
import warnings
from PIL import Image, UnidentifiedImageError

# Capture before the lazy YOLO import: its global Image.open patch attempts an
# optional HEIF plugin on decode failures, even for unsupported/corrupt uploads.
_open_image = Image.open

SUPPORTED_IMAGES = {'.jpg': ('image/jpeg', 'JPEG'), '.jpeg': ('image/jpeg', 'JPEG'),
                    '.png': ('image/png', 'PNG'), '.webp': ('image/webp', 'WEBP')}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000


def validate_image_upload(filename: str | None, content_type: str | None):
    if not filename or not filename.strip():
        raise ValueError('Image filename is required.')
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_IMAGES or content_type != SUPPORTED_IMAGES[extension][0]:
        raise ValueError('Use a JPG, JPEG, PNG or WebP image with a matching content type.')
    return SUPPORTED_IMAGES[extension][1]


def decode_image(data: bytes, expected_format: str) -> Image.Image:
    if not data:
        raise ValueError('Image file is empty.')
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError('Image must be at most 10 MiB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with _open_image(BytesIO(data), formats=[expected_format]) as image:
                if image.format != expected_format:
                    raise ValueError('Image contents do not match the uploaded format.')
                if image.width <= 0 or image.height <= 0 or image.width * image.height > MAX_IMAGE_PIXELS:
                    raise ValueError('Image dimensions are invalid or exceed 20 million pixels.')
                image.verify()
            with _open_image(BytesIO(data), formats=[expected_format]) as image:
                image.load()
                return image.convert('RGB')
    except ValueError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError('Image could not be decoded.') from exc
