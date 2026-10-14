"""Printable fee receipt (PDF)."""

import io

from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from core.models import SchoolProfile
from exams.pdf import draw_logo


def _rupees(value):
    return f"Rs {value:,.2f}"


def receipt_pdf(payment) -> bytes:
    invoice = payment.invoice
    student = invoice.student
    school = SchoolProfile.get()
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A5)
    width, height = A5
    left, right = 14 * mm, width - 14 * mm
    y = height - 16 * mm

    pdf.setTitle(f"Receipt {payment.receipt_number}")
    draw_logo(pdf, school, left, y + 5 * mm, 14 * mm)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawCentredString(width / 2, y, school.name)
    y -= 5 * mm
    pdf.setFont("Helvetica", 8)
    address = ", ".join(filter(None, [school.address, school.district, school.state, school.pincode]))
    if address:
        pdf.drawCentredString(width / 2, y, address[:110])
        y -= 4 * mm
    if school.phone:
        pdf.drawCentredString(width / 2, y, f"Phone {school.phone}")
        y -= 4 * mm
    y -= 3 * mm
    pdf.setFont("Helvetica-Bold", 12)
    title = "FEE RECEIPT" + (" (REVERSED)" if payment.status == payment.Status.REVERSED else "")
    pdf.drawCentredString(width / 2, y, title)
    y -= 9 * mm

    def row(label, value):
        nonlocal y
        pdf.setFont("Helvetica", 9)
        pdf.drawString(left, y, label)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(left + 38 * mm, y, str(value))
        y -= 5.5 * mm

    row("Receipt no.", payment.receipt_number)
    row("Date", payment.paid_on.strftime("%d %b %Y"))
    row("Student", student.full_name)
    row("Admission no.", student.admission_number)
    row("Class", f"{invoice.school_class.name} ({invoice.session.name})")
    row("Invoice", f"{invoice.number}" + (f" - {invoice.installment.name}" if invoice.installment else ""))
    row("Paid by", payment.get_mode_display() + (f" ({payment.reference})" if payment.reference else ""))
    y -= 2 * mm

    pdf.line(left, y, right, y)
    y -= 5 * mm
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(left, y, "Fee head")
    pdf.drawRightString(right - 30 * mm, y, "Amount")
    pdf.drawRightString(right, y, "After concession")
    y -= 5 * mm
    pdf.setFont("Helvetica", 9)
    for line in invoice.lines.select_related("fee_head"):
        pdf.drawString(left, y, line.fee_head.name)
        pdf.drawRightString(right - 30 * mm, y, _rupees(line.amount))
        pdf.drawRightString(right, y, _rupees(line.net))
        y -= 5 * mm
    pdf.line(left, y + 2 * mm, right, y + 2 * mm)
    y -= 3 * mm

    def total(label, value, bold=False):
        nonlocal y
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", 10 if bold else 9)
        pdf.drawString(left + 50 * mm, y, label)
        pdf.drawRightString(right, y, _rupees(value))
        y -= 5.5 * mm

    total("Invoice total", invoice.net_amount)
    total("Received now", payment.amount, bold=True)
    total("Balance after all payments", invoice.balance)

    pdf.setFont("Helvetica-Oblique", 7)
    pdf.drawString(left, 12 * mm, "This is a computer-generated receipt and does not need a signature.")
    pdf.showPage()
    pdf.save()
    return buf.getvalue()
