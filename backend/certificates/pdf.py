"""Transfer certificate PDF. PLACEHOLDER layout until the school gives its approved format."""

import io
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from core.models import SchoolProfile
from exams.pdf import _fit, school_header


def _d(value):
    return date.fromisoformat(value).strftime("%d/%m/%Y") if value else "-"


def tc_pdf(tc) -> bytes:
    d, school = tc.details, SchoolProfile.get()
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    left, right = 18 * mm, width - 18 * mm
    pdf.setTitle(f"Transfer certificate {tc.number}")
    y = school_header(pdf, school, width, height - 20 * mm)
    y -= 4 * mm
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawCentredString(width / 2, y, "TRANSFER CERTIFICATE")
    if tc.status == tc.Status.CANCELLED:
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawCentredString(width / 2, y - 6 * mm, f"CANCELLED: {tc.cancel_reason}"[:90])
        y -= 6 * mm
    y -= 10 * mm
    pdf.setFont("Helvetica", 9.5)
    pdf.drawString(left, y, f"TC no.: {tc.number}")
    pdf.drawRightString(right, y, f"Admission (S.R.) no.: {d.get('admission_number', '')}")
    y -= 10 * mm

    if tc.fees_due > 0:
        dues = f"Rs {tc.fees_due:,.2f} unpaid; issued with the principal's approval ({tc.dues_waived_reason})"
    else:
        dues = "All dues paid"
    rows = [
        ("Name of the student", d.get("name")),
        ("Father's name", d.get("father_name") or "-"),
        ("Mother's name", d.get("mother_name") or "-"),
        *([("Guardian's name", d["guardian_name"])] if d.get("guardian_name") else []),
        ("Nationality", d.get("nationality")),
        ("Category", d.get("category")),
        ("Date of birth (in figures)", _d(d.get("date_of_birth"))),
        ("Date of birth (in words)", d.get("date_of_birth_words")),
        ("Date of first admission and class", f"{_d(d.get('admission_date'))}, {d.get('admitted_in_class')}"),
        ("Class in which the student last studied", f"{d.get('last_class')} ({d.get('last_session')})"),
        ("Result of the last examination", tc.last_exam_result or "-"),
        ("Working days / days present (last session)",
         f"{d.get('working_days')} / {d.get('days_present')}" if d.get("working_days") else "-"),
        ("School dues", dues),
        ("General conduct", tc.conduct),
        ("Date of application for the certificate", tc.application_date.strftime("%d/%m/%Y")),
        ("Date the student left the school", tc.leaving_date.strftime("%d/%m/%Y")),
        ("Date of issue of the certificate", tc.issued_on.strftime("%d/%m/%Y") if tc.issued_on else "-"),
        ("Reason for leaving the school", tc.reason),
        ("Any other remarks", tc.remarks or "-"),
    ]
    label_w = 78 * mm
    for i, (label, value) in enumerate(rows, start=1):
        pdf.setFont("Helvetica", 9.5)
        pdf.drawString(left, y, f"{i}.")
        pdf.drawString(left + 7 * mm, y, label)
        pdf.setFont("Helvetica-Bold", 9.5)
        text = str(value or "-")
        width_left = right - left - label_w
        line = _fit(pdf, text, "Helvetica-Bold", 9.5, width_left)
        pdf.drawString(left + label_w, y, line)
        if len(line) < len(text):
            y -= 5 * mm
            pdf.drawString(left + label_w, y, _fit(pdf, text[len(line):].lstrip(), "Helvetica-Bold", 9.5, width_left))
        y -= 8 * mm

    sig_y = 35 * mm
    for i, label in enumerate(["Prepared by", "Checked by", "Principal (with seal)"]):
        x = left + i * (right - left) / 3
        pdf.line(x + 3 * mm, sig_y, x + 50 * mm, sig_y)
        pdf.setFont("Helvetica", 9)
        pdf.drawString(x + 3 * mm, sig_y - 5 * mm, label)
    pdf.showPage()
    pdf.save()
    return buf.getvalue()
