"""Report card PDF. PLACEHOLDER layout until the school gives its approved format."""

import io

from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from core.models import SchoolProfile

from .grading import CO_SCHOLASTIC_AREAS, bands
from .report import num


def school_header(pdf, school, width, y):
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(width / 2, y, school.name)
    y -= 5.5 * mm
    pdf.setFont("Helvetica", 8.5)
    address = ", ".join(filter(None, [school.address, school.district, school.state, school.pincode]))
    if address:
        pdf.drawCentredString(width / 2, y, address[:120])
        y -= 4 * mm
    extra = "   ".join(filter(None, [
        f"Phone {school.phone}" if school.phone else "", f"UDISE {school.udise_code}" if school.udise_code else "",
        f"Affiliation {school.affiliation_number}" if school.affiliation_number else "",
    ]))
    if extra:
        pdf.drawCentredString(width / 2, y, extra)
        y -= 4 * mm
    return y


def _fit(pdf, text, font, size, width):
    text = str(text)
    while text and pdf.stringWidth(text, font, size) > width:
        text = text[:-1]
    return text


def draw_report_card(pdf, term, card, school, scale):
    width, height = A4
    left, right = 15 * mm, width - 15 * mm
    y = school_header(pdf, school, width, height - 18 * mm)
    y -= 3 * mm
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawCentredString(width / 2, y, f"REPORT CARD: {term.name.upper()} {term.session.name}")
    y -= 10 * mm

    student, e = card["student"], card["enrollment"]
    info = [
        ("Name", student.full_name), ("Admission no.", student.admission_number),
        ("Class", f"{e.section.school_class.name} {e.section.name}"), ("Roll no.", e.roll_number or "-"),
        ("Father", card["guardians"]["father"] or "-"), ("Mother", card["guardians"]["mother"] or "-"),
        ("Date of birth", student.date_of_birth.strftime("%d %b %Y")), ("Attendance",
         f"{card['attendance']['present']} of {card['attendance']['marked']} days" if card["attendance"]["marked"] else "-"),
    ]
    for i, (label, value) in enumerate(info):
        x = left if i % 2 == 0 else width / 2 + 5 * mm
        pdf.setFont("Helvetica", 9)
        pdf.drawString(x, y, label)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(x + 27 * mm, y, _fit(pdf, value, "Helvetica-Bold", 9, 55 * mm))
        if i % 2 == 1:
            y -= 5.5 * mm
    y -= 4 * mm

    # Scholastic table: subject, one column per test, total, percent, grade.
    columns = card["columns"]
    subject_w = 48 * mm
    tail = [("Total", 24 * mm), ("%", 16 * mm), ("Grade", 14 * mm)]
    test_w = (right - left - subject_w - sum(w for _, w in tail)) / max(len(columns), 1)
    row_h = 6.5 * mm

    def grid_row(cells, bold=False, fill=False):
        nonlocal y
        if fill:
            pdf.setFillGray(0.9)
            pdf.rect(left, y - 2 * mm, right - left, row_h, stroke=0, fill=1)
            pdf.setFillGray(0)
        x = left
        for (text, w, align) in cells:
            font = "Helvetica-Bold" if bold else "Helvetica"
            pdf.setFont(font, 8.5)
            text = _fit(pdf, text, font, 8.5, w - 2 * mm)
            if align == "l":
                pdf.drawString(x + 1.5 * mm, y, text)
            else:
                pdf.drawCentredString(x + w / 2, y, text)
            x += w
        pdf.line(left, y - 2 * mm, right, y - 2 * mm)
        y -= row_h

    top = y + row_h - 2 * mm
    pdf.line(left, top, right, top)
    grid_row([("Subject", subject_w, "l")] + [(c, test_w, "c") for c in columns]
             + [(label, w, "c") for label, w in tail], bold=True, fill=True)
    for s in card["subjects"]:
        grid_row([(s["subject"], subject_w, "l")] + [(s["scores"].get(c, ""), test_w, "c") for c in columns] + [
            (f"{num(s['obtained'])}/{num(s['maximum'])}" if s["maximum"] else "-", tail[0][1], "c"),
            (f"{s['percent']:.1f}" if s["percent"] is not None else "-", tail[1][1], "c"),
            (s["grade"] or "-", tail[2][1], "c"),
        ])
    if not card["subjects"]:
        grid_row([("No marks have been entered for this term.", right - left, "l")])
    grid_row([("Overall", subject_w, "l")] + [("", test_w, "c") for _ in columns] + [
        (f"{num(card['obtained'])}/{num(card['maximum'])}" if card["maximum"] else "-", tail[0][1], "c"),
        (f"{card['percent']:.1f}" if card["percent"] is not None else "-", tail[1][1], "c"),
        (card["grade"] or "-", tail[2][1], "c"),
    ], bold=True, fill=True)
    # Vertical lines of the table.
    bottom = y + row_h - 2 * mm
    x = left
    for w in [subject_w] + [test_w] * len(columns) + [w for _, w in tail]:
        pdf.line(x, top, x, bottom)
        x += w
    pdf.line(right, top, right, bottom)
    y -= 4 * mm

    pdf.setFont("Helvetica-Bold", 10)
    result = card["result"] or "-"
    if card["failed_subjects"]:
        result += f" (improve in: {', '.join(card['failed_subjects'])})"
    pdf.drawString(left, y, _fit(pdf, f"Result: {result}", "Helvetica-Bold", 10, right - left))
    y -= 9 * mm

    pdf.setFont("Helvetica-Bold", 9.5)
    pdf.drawString(left, y, "Co-scholastic areas")
    y -= 5.5 * mm
    pdf.setFont("Helvetica", 9)
    areas = list(CO_SCHOLASTIC_AREAS) + [a for a in card["co_scholastic"] if a not in CO_SCHOLASTIC_AREAS]
    for i, area in enumerate(areas):
        x = left + (i % 3) * 60 * mm
        pdf.drawString(x, y, f"{area}: {card['co_scholastic'].get(area) or '-'}")
        if i % 3 == 2 or i == len(areas) - 1:
            y -= 5 * mm
    y -= 4 * mm

    pdf.setFont("Helvetica-Bold", 9.5)
    pdf.drawString(left, y, "Class teacher's remark")
    y -= 5.5 * mm
    pdf.setFont("Helvetica", 9)
    remark = card["remark"] or "-"
    while remark:
        line = _fit(pdf, remark, "Helvetica", 9, right - left)
        if len(line) < len(remark) and " " in line:
            line = line[: line.rfind(" ")]
        pdf.drawString(left, y, line)
        remark = remark[len(line):].lstrip()
        y -= 4.5 * mm

    # Signatures.
    sig_y = 40 * mm
    for i, label in enumerate(["Class teacher", "Principal", "Parent"]):
        x = left + i * (right - left) / 3
        pdf.line(x + 5 * mm, sig_y, x + 50 * mm, sig_y)
        pdf.setFont("Helvetica", 8.5)
        pdf.drawString(x + 5 * mm, sig_y - 4.5 * mm, label)

    pdf.setFont("Helvetica", 7)
    scale_text = "Grades: " + ", ".join(
        f"{g} {num(m)}%+" if m else f"{g} below {num(prev)}%" for (g, m, _d, _p), prev in
        zip(scale, [None] + [r[1] for r in scale])
    )
    pdf.drawString(left, 24 * mm, _fit(pdf, scale_text, "Helvetica", 7, right - left))
    pdf.drawString(left, 20 * mm, f"Generated on {timezone.localdate():%d %b %Y}.")


def report_cards_pdf(term, cards) -> bytes:
    school, scale = SchoolProfile.get(), bands()
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    pdf.setTitle(f"Report cards {term}")
    for card in cards:
        draw_report_card(pdf, term, card, school, scale)
        pdf.showPage()
    if not cards:
        pdf.drawString(20 * mm, 270 * mm, "No students.")
        pdf.showPage()
    pdf.save()
    return buf.getvalue()
