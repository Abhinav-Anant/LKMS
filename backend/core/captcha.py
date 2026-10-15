"""A self-hosted picture CAPTCHA for the public forms. No outside service, no keys.

1. GET  /captcha/          -> a picture of 5 letters and a signed `challenge`.
2. POST /captcha/          -> {challenge, answer}; a right answer returns a signed `pass`.
3. The form sends `captcha` = that pass; the view calls `require(request)`.

Each challenge and each pass works once (remembered in UsedCaptcha), so one solve cannot be replayed.
"""
import base64
import io
import random
import secrets
from datetime import timedelta

from django.core import signing
from django.db import IntegrityError
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from rest_framework.exceptions import ValidationError

LETTERS = "ABCDEFGHJKMNPRSTUVWXYZ23456789"  # no 0/O, 1/I/L, Q
LENGTH = 5
CHALLENGE_AGE = 10 * 60  # seconds to type the letters
PASS_AGE = 60 * 60  # seconds to fill the form after solving


def enabled():
    from .models import SchoolProfile

    return SchoolProfile.get().captcha_enabled


def _answer_hash(nonce, answer):
    return salted_hmac("lkms.captcha", f"{nonce}:{answer.strip().upper()}").hexdigest()


def _picture(text):
    rng = random.SystemRandom()
    width, height = 200, 70
    image = Image.new("RGB", (width, height), (245, 245, 245))
    draw = ImageDraw.Draw(image)
    for _ in range(6):
        draw.line([(rng.randint(0, width), rng.randint(0, height)) for _ in range(2)],
                  fill=tuple(rng.randint(120, 200) for _ in range(3)), width=2)
    font = ImageFont.load_default(size=40)
    for i, char in enumerate(text):
        glyph = Image.new("RGBA", (50, 60), (0, 0, 0, 0))
        ImageDraw.Draw(glyph).text((8, 4), char, font=font, fill=tuple(rng.randint(0, 90) for _ in range(3)))
        glyph = glyph.rotate(rng.uniform(-18, 18), resample=Image.BICUBIC, expand=False)
        image.paste(glyph, (8 + i * 37 + rng.randint(-4, 4), rng.randint(0, 12)), glyph)
    for _ in range(300):
        draw.point((rng.randint(0, width - 1), rng.randint(0, height - 1)), fill=tuple(rng.randint(60, 200) for _ in range(3)))
    out = io.BytesIO()
    image.filter(ImageFilter.SMOOTH).save(out, format="PNG")
    return "data:image/png;base64," + base64.b64encode(out.getvalue()).decode()


def new_challenge():
    text = "".join(secrets.choice(LETTERS) for _ in range(LENGTH))
    nonce = secrets.token_urlsafe(12)
    challenge = signing.dumps({"n": nonce, "h": _answer_hash(nonce, text)}, salt="lkms.captcha.challenge")
    return {"challenge": challenge, "image": _picture(text)}


def _use_once(nonce):
    """True the first time a nonce is seen; False on a replay."""
    from .models import UsedCaptcha

    UsedCaptcha.objects.filter(used_at__lt=timezone.now() - timedelta(seconds=2 * PASS_AGE)).delete()
    try:
        UsedCaptcha.objects.create(nonce=nonce)
    except IntegrityError:
        return False
    return True


def verify_answer(challenge, answer):
    """Checks the typed letters. Returns a pass token, or None. A challenge can be tried only once."""
    try:
        data = signing.loads(challenge or "", salt="lkms.captcha.challenge", max_age=CHALLENGE_AGE)
    except signing.BadSignature:
        return None
    if not _use_once(data["n"]) or not constant_time_compare(data["h"], _answer_hash(data["n"], answer or "")):
        return None
    return signing.dumps({"n": secrets.token_urlsafe(12)}, salt="lkms.captcha.pass")


def require(request):
    """Call at the top of a public form's POST. Raises a 400 unless the form carries a fresh, unused pass."""
    if not enabled():
        return
    try:
        data = signing.loads(request.data.get("captcha") or "", salt="lkms.captcha.pass", max_age=PASS_AGE)
    except signing.BadSignature:
        data = None
    if data is None or not _use_once(data["n"]):
        raise ValidationError({"captcha": ["Please type the letters from the picture again."]})
