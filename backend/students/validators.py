import re

from django.core.exceptions import ValidationError


def validate_indian_mobile(value):
    if not re.fullmatch(r"[6-9]\d{9}", value or ""):
        raise ValidationError("Enter a 10-digit Indian mobile number.")


def validate_aadhaar(value):
    if value and not re.fullmatch(r"\d{12}", value):
        raise ValidationError("Aadhaar number must be 12 digits.")


def validate_pincode(value):
    if value and not re.fullmatch(r"[1-9]\d{5}", value):
        raise ValidationError("Enter a 6-digit PIN code.")


def normalise_mobile(value):
    """Strip spaces, dashes and a leading +91 / 0 so numbers compare equal."""
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits
