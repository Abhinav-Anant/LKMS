"""The grading scale and co-scholastic areas.

PLACEHOLDER until Lotus Kids confirms the scale it uses (see docs/BOARD_CHECKS.md).
The school edits the scale in the app (Exams > Grade scale); these defaults are used
only when no scale has been saved.
"""

from decimal import ROUND_HALF_UP, Decimal

DEFAULT_BANDS = [
    # grade, minimum percent, description, counts as a pass
    ("A+", 90, "Outstanding", True),
    ("A", 75, "Excellent", True),
    ("B", 60, "Very good", True),
    ("C", 45, "Good", True),
    ("D", 33, "Satisfactory", True),
    ("E", 0, "Needs improvement", False),
]

CO_SCHOLASTIC_AREAS = ["Art and craft", "Music and dance", "Games and sports", "Discipline", "Cleanliness"]
CO_SCHOLASTIC_GRADES = ["A", "B", "C"]


def bands():
    from .models import GradeBand

    saved = [(b.grade, b.min_percent, b.description, b.is_pass) for b in GradeBand.objects.all()]
    rows = saved or [(g, Decimal(m), d, p) for g, m, d, p in DEFAULT_BANDS]
    return sorted(rows, key=lambda r: r[1], reverse=True)


def grade_for(percent, scale=None):
    """Return (grade, is_pass) for a percentage, or ("", None) when there is nothing to grade."""
    if percent is None:
        return "", None
    for grade, minimum, _description, is_pass in scale or bands():
        if percent >= minimum:
            return grade, is_pass
    return "", False


def percent(obtained, maximum):
    if not maximum:
        return None
    return (Decimal(obtained) * 100 / Decimal(maximum)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
