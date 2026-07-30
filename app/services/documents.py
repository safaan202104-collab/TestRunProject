"""
Document Generation Service for MyGlowTheory.
Generates PDF appointment confirmations and treatment plan invoices.
"""
import os
import io
from datetime import datetime
from typing import Dict, Any, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

# Brand colors
BRAND_PRIMARY = HexColor("#7c3aed")   # Purple
BRAND_DARK = HexColor("#1e1b4b")      # Deep indigo
BRAND_LIGHT = HexColor("#f5f3ff")     # Light purple
BRAND_ACCENT = HexColor("#a78bfa")    # Soft violet
TEXT_DARK = HexColor("#1f2937")
TEXT_MUTED = HexColor("#6b7280")
WHITE = HexColor("#ffffff")

DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "runtime", "docs"))
os.makedirs(DOCS_DIR, exist_ok=True)


def _get_styles():
    """Returns custom paragraph styles for the PDF."""
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        "BrandTitle",
        parent=styles["Title"],
        fontSize=22,
        textColor=BRAND_PRIMARY,
        spaceAfter=6,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "BrandSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=TEXT_MUTED,
        alignment=TA_CENTER,
        spaceAfter=20,
    ))
    styles.add(ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=BRAND_DARK,
        spaceBefore=14,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "BodyText2",
        parent=styles["Normal"],
        fontSize=10,
        textColor=TEXT_DARK,
        leading=14,
    ))
    styles.add(ParagraphStyle(
        "FooterText",
        parent=styles["Normal"],
        fontSize=8,
        textColor=TEXT_MUTED,
        alignment=TA_CENTER,
    ))
    return styles


def generate_appointment_confirmation(
    appointment: Dict[str, Any],
    patient_name: str = "Patient",
    provider_name: str = "Provider",
    service_name: str = "Service",
) -> str:
    """
    Generates a PDF appointment confirmation letter.
    Returns the absolute path to the generated PDF.
    """
    appt_id = appointment.get("id", "N/A")
    start_time = appointment.get("start", "N/A")
    duration = appointment.get("duration", 30)
    price = appointment.get("price", 0.0)
    status = appointment.get("status", "confirmed")

    filename = f"confirmation_{appt_id}.pdf"
    filepath = os.path.join(DOCS_DIR, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = _get_styles()
    story = []

    # Header
    story.append(Paragraph("✦ MyGlowTheory", styles["BrandTitle"]))
    story.append(Paragraph("AI-Powered Medical Aesthetics · Appointment Confirmation", styles["BrandSubtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_ACCENT, spaceAfter=16))

    # Confirmation badge
    story.append(Paragraph(f"Status: <b>{status.upper()}</b>", styles["SectionHeader"]))
    story.append(Spacer(1, 8))

    # Appointment details table
    detail_data = [
        ["Confirmation #", appt_id],
        ["Patient", patient_name],
        ["Provider", provider_name],
        ["Service", service_name],
        ["Date & Time", start_time],
        ["Duration", f"{duration} minutes"],
        ["Price", f"${price:,.2f} USD"],
    ]

    detail_table = Table(detail_data, colWidths=[2.2 * inch, 4.5 * inch])
    detail_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), BRAND_LIGHT),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_DARK),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, BRAND_ACCENT),
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 20))

    # Important notes
    story.append(Paragraph("Important Information", styles["SectionHeader"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_ACCENT, spaceAfter=8))
    notes = [
        "Please arrive 10 minutes before your scheduled appointment time.",
        "Cancellations must be made at least 24 hours in advance.",
        "Bring a valid photo ID and your insurance card (if applicable).",
        "Avoid blood-thinning medications (aspirin, ibuprofen) for 48 hours before injectable treatments.",
    ]
    for note in notes:
        story.append(Paragraph(f"• {note}", styles["BodyText2"]))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 30))

    # Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=TEXT_MUTED, spaceAfter=8))
    story.append(Paragraph(
        f"Generated by MyGlowTheory AI Decision Platform · {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        styles["FooterText"],
    ))
    story.append(Paragraph(
        "This is an automated confirmation. If you have questions, please contact the clinic directly.",
        styles["FooterText"],
    ))

    doc.build(story)
    return filepath


def generate_invoice(
    appointment: Dict[str, Any],
    patient_name: str = "Patient",
    provider_name: str = "Provider",
    service_name: str = "Service",
) -> str:
    """
    Generates a PDF treatment plan invoice.
    Returns the absolute path to the generated PDF.
    """
    appt_id = appointment.get("id", "N/A")
    price = appointment.get("price", 0.0)
    duration = appointment.get("duration", 30)
    start_time = appointment.get("start", "N/A")

    filename = f"invoice_{appt_id}.pdf"
    filepath = os.path.join(DOCS_DIR, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = _get_styles()
    story = []

    # Header
    story.append(Paragraph("✦ MyGlowTheory", styles["BrandTitle"]))
    story.append(Paragraph("Treatment Plan Invoice", styles["BrandSubtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_ACCENT, spaceAfter=16))

    # Bill To
    story.append(Paragraph("Bill To", styles["SectionHeader"]))
    story.append(Paragraph(patient_name, styles["BodyText2"]))
    story.append(Spacer(1, 12))

    # Line items table
    line_items = [
        ["#", "Service", "Provider", "Duration", "Amount"],
        ["1", service_name, provider_name, f"{duration} min", f"${price:,.2f}"],
    ]

    item_table = Table(line_items, colWidths=[0.5 * inch, 2.5 * inch, 2 * inch, 1 * inch, 1.2 * inch])
    item_table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        # Body
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("BACKGROUND", (0, 1), (-1, -1), BRAND_LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, BRAND_ACCENT),
        ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
    ]))
    story.append(item_table)
    story.append(Spacer(1, 12))

    # Totals
    totals_data = [
        ["Subtotal", f"${price:,.2f}"],
        ["Tax (0%)", "$0.00"],
        ["Total Due", f"${price:,.2f}"],
    ]
    totals_table = Table(totals_data, colWidths=[5.5 * inch, 1.7 * inch])
    totals_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, -1), (-1, -1), BRAND_PRIMARY),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEABOVE", (0, -1), (-1, -1), 1, BRAND_DARK),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 30))

    # Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=TEXT_MUTED, spaceAfter=8))
    story.append(Paragraph(
        f"Invoice generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} · Ref: {appt_id}",
        styles["FooterText"],
    ))
    story.append(Paragraph(
        "Payment is due at the time of service. Thank you for choosing MyGlowTheory.",
        styles["FooterText"],
    ))

    doc.build(story)
    return filepath
