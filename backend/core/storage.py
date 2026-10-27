"""Private file storage for student documents and photos.

Files live under settings.PRIVATE_MEDIA_ROOT with random names. There is no
public URL for them: they are streamed through views that check permissions
and write an audit entry (see `private_file_response`).
"""

import hashlib
import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.http import FileResponse
from django.utils.deconstruct import deconstructible


class PrivateStorage(FileSystemStorage):
    """Reads PRIVATE_MEDIA_ROOT on every use, so it always follows the current settings."""

    @property
    def base_location(self):
        return str(settings.PRIVATE_MEDIA_ROOT)

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    @property
    def base_url(self):
        return None


private_storage = PrivateStorage()


def get_private_storage():
    return private_storage


@deconstructible
class RandomPath:
    """upload_to callable that keeps only a random name and the detected extension."""

    def __init__(self, folder):
        self.folder = folder

    def __call__(self, instance, filename):
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
        return f"{self.folder}/{uuid.uuid4().hex}.{ext}"

    def __eq__(self, other):
        return isinstance(other, RandomPath) and other.folder == self.folder


# Accepted formats, identified by their first bytes rather than the name or the
# browser-supplied content type, both of which the uploader controls.
SIGNATURES = {
    "pdf": (b"%PDF-", "application/pdf"),
    "jpg": (b"\xff\xd8\xff", "image/jpeg"),
    "png": (b"\x89PNG\r\n\x1a\n", "image/png"),
}


def detect_type(uploaded_file):
    uploaded_file.seek(0)
    head = uploaded_file.read(16)
    uploaded_file.seek(0)
    for ext, (magic, mime) in SIGNATURES.items():
        if head.startswith(magic):
            return ext, mime
    return None, None


def validate_upload(uploaded_file, allowed=("pdf", "jpg", "png"), max_mb=None):
    """Check size and real file type. Returns (extension, content_type, sha256)."""
    max_mb = max_mb or settings.MAX_UPLOAD_SIZE_MB
    if uploaded_file.size > max_mb * 1024 * 1024:
        raise ValidationError(f"File is larger than {max_mb} MB.")
    if uploaded_file.size == 0:
        raise ValidationError("File is empty.")

    ext, mime = detect_type(uploaded_file)
    if ext not in allowed:
        raise ValidationError("Only " + ", ".join(a.upper() for a in allowed) + " files are accepted.")

    if ext in ("jpg", "png"):
        from PIL import Image

        try:
            with Image.open(uploaded_file) as img:
                img.verify()
        except Exception as exc:
            raise ValidationError("The image file is damaged or not a real image.") from exc
        finally:
            uploaded_file.seek(0)

    digest = hashlib.sha256()
    for chunk in uploaded_file.chunks():
        digest.update(chunk)
    uploaded_file.seek(0)
    uploaded_file.name = f"upload.{ext}"
    return ext, mime, digest.hexdigest()


def private_file_response(field_file, content_type, download_name):
    response = FileResponse(field_file.open("rb"), content_type=content_type)
    response["Content-Disposition"] = f'inline; filename="{download_name}"'
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
