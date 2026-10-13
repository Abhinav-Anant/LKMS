from contextlib import contextmanager

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError


@contextmanager
def as_api_errors():
    """Turn validation errors raised by the services into 400 responses."""
    try:
        yield
    except DjangoValidationError as exc:
        raise ValidationError(exc.message_dict if hasattr(exc, "error_dict") else exc.messages) from exc
