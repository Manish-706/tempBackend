from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime
import os
import re
import qrcode
from io import BytesIO

def sanitize_filename(text):
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', text)

def generate_qr_code(data):
    qr = qrcode.make(data)
    buffer = BytesIO()
    qr.save(buffer, format='PNG')
    buffer.seek(0)
    return ImageReader(buffer)

def format_date(date_str):
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', ''))
        return dt.strftime('%a, %d %b %Y %H:%M hrs')
    except:
        return date_str

def generate_ticket_pdf(order_data, save_path="tickets"):
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    order_id = sanitize_filename(order_data["id"])
    pnr = sanitize_filename(order_data["associatedRecords"][0]["reference"])
    traveler = order_data["travelers"][0]
    flight_offer = order_data["flightOffers"][0]
    itineraries = flight_offer["itineraries"]

    # Detect trip type
    if len(itineraries) == 1:
        trip_type = "One-way"
    elif len(itineraries) == 2:
        trip_type = "Round-trip"
    else:
        trip_type = "Multicity"

    filename = f"{pnr}_{order_id}.pdf"
    full_path = os.path.join(save_path, filename)

    c = canvas.Canvas(full_path, pagesize=A4)
    width, height = A4

    styles = getSampleStyleSheet()
    footer_y = 40
    y_position = height - 40

    # --- LOGO ---
    logo_path = os.path.join("static", "logo.png")
    if os.path.exists(logo_path):
        logo = ImageReader(logo_path)
        c.drawImage(logo, 40, y_position - 40, width=100, height=30, mask='auto')

    y_position -= 60
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor('#1A237E'))
    c.drawString(40, y_position, "E-TICKET")

    # Booking Info
    c.setFont("Helvetica", 10)
    y_position -= 20
    c.setFillColor(colors.black)
    c.drawString(40, y_position, f"Booking ID: {order_id}")
    y_position -= 15
    c.drawString(40, y_position, f"Booking Date: {datetime.now().strftime('%a, %d %b %Y')}")
    y_position -= 15
    c.drawString(40, y_position, f"Trip Type: {trip_type}")

    # Passenger Info Table
    y_position -= 25
    passenger_data = [
        ["Passenger Name", "Type", "Airline PNR", "E-Ticket Number"],
        [f"{traveler['name']['firstName']} {traveler['name']['lastName']}",
         "Adult", pnr, pnr]
    ]
    p_table = Table(passenger_data, colWidths=[120, 80, 120, 120])
    p_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#BBDEFB')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ]))
    p_table.wrapOn(c, width, height)
    p_table_height = 45
    p_table.drawOn(c, 40, y_position - p_table_height)
    y_position -= p_table_height + 30

    # Iterate through all itineraries (for round-trip/multicity)
    for idx, itinerary in enumerate(itineraries):
        c.setFont("Helvetica-Bold", 12)
        if trip_type != "One-way":
            c.drawString(40, y_position, f"Flight Itinerary {idx + 1}")
        else:
            c.drawString(40, y_position, "Flight Itinerary")
        y_position -= 20

        # Flight Table
        flight_table_data = [["Carrier", "Departure", "Arrival", "Duration", "Class"]]
        for seg in itinerary["segments"]:
            departure = seg["departure"]
            arrival = seg["arrival"]
            duration = seg["duration"].replace('PT', '').replace('H', 'h ').replace('M', 'm')
            flight_table_data.append([
                seg["carrierCode"],
                f"{departure['iataCode']} Terminal {departure.get('terminal', '--')}\n{format_date(departure['at'])}",
                f"{arrival['iataCode']} Terminal {arrival.get('terminal', '--')}\n{format_date(arrival['at'])}",
                duration,
                flight_offer.get('class', ['--'])[0].upper()
            ])

        f_table = Table(flight_table_data, colWidths=[60, 150, 150, 80, 60])
        f_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E3F2FD')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        f_table.wrapOn(c, width, height)
        f_table_height = len(flight_table_data) * 30
        f_table.drawOn(c, 40, y_position - f_table_height)
        y_position -= f_table_height + 30

    # Baggage Allowance
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y_position, "Baggage Allowance")
    y_position -= 20

    baggage_data = [["Airline", "Segment", "Adult", "Child"]]
    for itinerary in itineraries:
        for seg in itinerary["segments"]:
            baggage_data.append([
                seg["carrierCode"],
                f"{seg['departure']['iataCode']}-{seg['arrival']['iataCode']}",
                "30 KG", "30 KG"
            ])

    b_table = Table(baggage_data, colWidths=[100, 100, 80, 80])
    b_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E3F2FD')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ]))
    b_table.wrapOn(c, width, height)
    b_table_height = len(baggage_data) * 20
    b_table.drawOn(c, 40, y_position - b_table_height)
    y_position -= b_table_height + 30

    # Payment Summary
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.black)
    c.drawString(40, y_position, "Payment Summary")
    y_position -= 20

    price_info = flight_offer["price"]
    base = float(price_info.get("base", 0))
    total = float(price_info.get("total", 0))
    currency = price_info.get("currency", "INR")
    fees = price_info.get("fees", [])

    payment_data = [["Description", "Amount"]]
    payment_data.append(["Base Fare", f"{currency} {base:,.2f}"])

    total_fees = 0
    for fee in fees:
        amount = float(fee.get("amount", 0))
        fee_type = fee.get("type", "OTHER").capitalize()
        total_fees += amount
        payment_data.append([f"{fee_type} Fee", f"{currency} {amount:,.2f}"])

    payment_data.append(["Total Amount Paid", f"{currency} {total:,.2f}"])

    pay_table = Table(payment_data, colWidths=[200, 150])
    pay_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E3F2FD')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ]))

    row_height = 20
    pay_table_height = len(payment_data) * row_height
    pay_table.wrapOn(c, width, height)
    pay_table.drawOn(c, 40, y_position - pay_table_height)
    y_position -= pay_table_height + 30

    # Terms and Conditions
    terms_style = ParagraphStyle('TermsStyle', parent=styles['Normal'], fontSize=9, leading=12, spaceAfter=6)
    terms = [
        Paragraph("<b>How to cancel:</b> You can cancel your booking through our website. Cancellations within 3 hours of departure must contact airline directly.", terms_style),
        Paragraph("<b>Refund Policy:</b> Refunds processed within 3-5 working days. Allow 7-14 days for bank processing.", terms_style),
        Paragraph("<b>Name Changes:</b> Not allowed. Cancel existing booking and create new one for name changes.", terms_style),
    ]

    for term in terms:
        term.wrapOn(c, width - 80, 50)
        term.drawOn(c, 40, y_position)
        y_position -= 30

    # QR Code
    qr_img = generate_qr_code(pnr)
    c.drawImage(qr_img, width - 120, footer_y - 20, width=60, height=60)

    # Footer
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.grey)
    c.drawString(40, footer_y, "Customer Care: support@travelbooking.com | +91-9999999999")
    c.drawString(40, footer_y - 15, "This ticket is issued by TravelBooking Inc. and is valid only with valid government ID.")

    c.showPage()
    c.save()
    return full_path
