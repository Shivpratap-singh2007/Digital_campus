import io
import os
import uuid
from pathlib import Path
from PIL import Image, ImageOps
from werkzeug.datastructures import FileStorage
from flask import current_app

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
ALLOWED_FORMATS = {"JPEG", "PNG"}


def validate_and_process_image(
    file_storage: FileStorage,
) -> tuple[bool, str, dict | None]:
    """
    Validates and securely processes uploaded image:
    1. Checks file size against MAX_IMAGE_FILE_SIZE (default 5 MB).
    2. Validates decoded image format using Pillow (JPEG or PNG).
    3. Checks pixel dimensions against MAX_IMAGE_PIXELS to prevent decompression bombs.
    4. Strips all EXIF/metadata by re-encoding clean pixels.
    5. Generates a secure random filename.
    6. Saves to UPLOAD_FOLDER outside static/.
    
    Returns: (success: bool, error_msg: str, metadata: dict | None)
    """
    if not file_storage or not file_storage.filename:
        return False, "No file provided", None

    # Check file size by reading stream
    file_storage.seek(0, os.SEEK_END)
    size_bytes = file_storage.tell()
    file_storage.seek(0)

    max_size = current_app.config.get("MAX_IMAGE_FILE_SIZE", 5 * 1024 * 1024)
    if size_bytes > max_size:
        return False, f"File size exceeds maximum allowed limit of {max_size // (1024 * 1024)} MB.", None

    if size_bytes == 0:
        return False, "Uploaded file is empty.", None

    # Open image with Pillow to verify real format and decode
    try:
        # Enforce pixel limit in Pillow
        max_pixels = current_app.config.get("MAX_IMAGE_PIXELS", 16_000_000)
        Image.MAX_IMAGE_PIXELS = max_pixels

        img_bytes = file_storage.read()
        file_storage.seek(0)
        
        with Image.open(io.BytesIO(img_bytes)) as img:
            img_format = img.format
            if not img_format or img_format.upper() not in ALLOWED_FORMATS:
                return (
                    False,
                    f"Invalid image format '{img_format}'. Only genuine JPEG and PNG images are accepted.",
                    None,
                )

            # Check pixel dimensions
            width, height = img.size
            if (width * height) > max_pixels:
                return (
                    False,
                    f"Image resolution ({width}x{height}) exceeds the safety limit of {max_pixels} pixels.",
                    None,
                )

            # Strip EXIF metadata and auto-orient
            # Converting to RGB (for JPEG) or RGBA (for PNG with alpha)
            target_ext = "jpg" if img_format.upper() == "JPEG" else "png"
            target_save_format = "JPEG" if target_ext == "jpg" else "PNG"
            mime_type = "image/jpeg" if target_ext == "jpg" else "image/png"

            # Create clean copy without any metadata/EXIF dictionaries
            if target_ext == "jpg":
                # Convert RGBA/P/LA to RGB
                clean_img = ImageOps.exif_transpose(img)
                if clean_img.mode != "RGB":
                    clean_img = clean_img.convert("RGB")
                save_kwargs = {"quality": 90, "optimize": True}
            else:
                clean_img = ImageOps.exif_transpose(img)
                if clean_img.mode not in ("RGB", "RGBA"):
                    clean_img = clean_img.convert("RGBA")
                save_kwargs = {"optimize": True}

            # Generate random unique filename
            unique_filename = f"{uuid.uuid4().hex}.{target_ext}"
            upload_dir = Path(current_app.config.get("UPLOAD_FOLDER"))
            upload_dir.mkdir(parents=True, exist_ok=True)
            save_path = upload_dir / unique_filename

            # Save clean image file
            clean_img.save(save_path, format=target_save_format, **save_kwargs)
            actual_saved_size = save_path.stat().st_size

            metadata = {
                "filename": unique_filename,
                "original_filename": Path(file_storage.filename).name[:250],
                "file_size": actual_saved_size,
                "mime_type": mime_type,
                "width": width,
                "height": height,
            }

            return True, "", metadata

    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        return False, "Image rejected: Exceeds safe pixel expansion limits (possible decompression bomb).", None
    except Exception as e:
        return False, f"Could not process image: corrupted file or invalid encoding. ({type(e).__name__})", None
