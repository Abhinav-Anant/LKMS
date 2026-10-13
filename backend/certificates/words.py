"""Dates in words, as transfer certificates print the date of birth."""

ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve",
        "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
ORDINALS = {"One": "First", "Two": "Second", "Three": "Third", "Five": "Fifth", "Eight": "Eighth", "Nine": "Ninth",
            "Twelve": "Twelfth", "Twenty": "Twentieth", "Thirty": "Thirtieth"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


def number_words(n):
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + (f" {ONES[n % 10]}" if n % 10 else "")
    if n < 1000:
        return f"{ONES[n // 100]} Hundred" + (f" {number_words(n % 100)}" if n % 100 else "")
    return f"{number_words(n // 1000)} Thousand" + (f" {number_words(n % 1000)}" if n % 1000 else "")


def ordinal_words(n):
    words = number_words(n).split(" ")
    last = words[-1]
    words[-1] = ORDINALS.get(last, last + "th")
    return " ".join(words)


def date_words(d):
    """date(2019, 1, 10) -> "Tenth January Two Thousand Nineteen"."""
    return f"{ordinal_words(d.day)} {MONTHS[d.month - 1]} {number_words(d.year)}"
