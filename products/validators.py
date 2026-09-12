import os
from django.core.exceptions import ValidationError
from PIL import Image

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp')

def validate_image_file(file):
    """
    Validate uploaded image files:
    1. Enforce max file size limit (5MB).
    2. Enforce allowed image extension whitelist.
    3. Verify file is a valid image using Pillow.
    """
    if file.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError(f"Image file size must not exceed {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)} MB.")

    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}.")

    # Verify actual image content with Pillow
    try:
        image = Image.open(file)
        image.verify()
    except Exception:
        raise ValidationError("Uploaded file is not a valid or readable image.")
    finally:
        # Reset file pointer after Pillow read
        if hasattr(file, 'seek'):
            file.seek(0)
