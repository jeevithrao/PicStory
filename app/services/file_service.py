# app/services/file_service.py
# Handles all file I/O: ZIP extraction, folder creation, path helpers.

import os
import zipfile
import shutil
from pathlib import Path
from app.config import settings

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def get_project_upload_dir(project_id: str) -> str:
    """Returns (and creates) the folder where a project's images are stored."""
    path = os.path.join(settings.UPLOAD_DIR, project_id)
    os.makedirs(path, exist_ok=True)
    return path


def get_project_output_dir(project_id: str) -> str:
    """Returns (and creates) the folder where a project's outputs are saved."""
    path = os.path.join(settings.OUTPUT_DIR, project_id)
    os.makedirs(path, exist_ok=True)
    return path


def extract_zip(zip_bytes: bytes, project_id: str) -> list[str]:
    """
    Extract images from a ZIP file's bytes.
    Ignores hidden files, non-image files, and nested folders deeper than 1 level.
    Returns list of absolute file paths to extracted images.
    Raises ValueError if no valid images found.
    """
    project_dir = get_project_upload_dir(project_id)
    extracted = []

    # Write zip to a temp file then extract
    temp_zip = os.path.join(project_dir, "_upload.zip")
    with open(temp_zip, "wb") as f:
        f.write(zip_bytes)

    with zipfile.ZipFile(temp_zip, "r") as zf:
        for member in zf.infolist():
            # Skip directories and hidden files
            if member.is_dir():
                continue
            filename = os.path.basename(member.filename)
            if filename.startswith(".") or filename.startswith("__"):
                continue

            # Only extract allowed image types
            ext = Path(filename).suffix.lower()
            if ext not in ALLOWED_IMAGE_EXTENSIONS:
                continue

            # Prevent path traversal attacks
            safe_path = os.path.join(project_dir, filename)
            with zf.open(member) as src, open(safe_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted.append(safe_path)

    os.remove(temp_zip)  # Clean up temp zip

    if not extracted:
        raise ValueError("No valid images found in the ZIP.")

    if len(extracted) > settings.MAX_IMAGES:
        # Keep only the first MAX_IMAGES
        for extra in extracted[settings.MAX_IMAGES:]:
            os.remove(extra)
        extracted = extracted[:settings.MAX_IMAGES]

    return sorted(extracted)  # Sort for consistent ordering


def save_generated_image(image_obj, filename: str, project_id: str) -> str:
    """
    Save a PIL Image object to the project's upload directory.
    Used by Mode 2 (Stable Diffusion output).
    Returns the absolute file path.
    """
    project_dir = get_project_upload_dir(project_id)
    path = os.path.join(project_dir, filename)
    image_obj.save(path)
    return path


def list_project_images(project_id: str) -> list[str]:
    """Return all image file paths in a project's upload directory."""
    project_dir = get_project_upload_dir(project_id)
    return sorted([
        os.path.join(project_dir, f)
        for f in os.listdir(project_dir)
        if Path(f).suffix.lower() in ALLOWED_IMAGE_EXTENSIONS
    ])


def relative_path(absolute_path: str) -> str:
    """Convert absolute path to a URL-safe relative path (always forward slashes)."""
    return os.path.relpath(absolute_path).replace("\\", "/")