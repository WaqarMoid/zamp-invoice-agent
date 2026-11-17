import json
import logging
from decimal import Decimal
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image, ImageFilter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.rules.dates import parse_date
from app.schemas import BankDetails, ExtractedInvoice, ExtractedLine, TaxBreakdown

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("generate_fixtures")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SEED_DATA_DIR = ROOT_DIR / "backend" / "app" / "seed_data"
FIXTURES_DIR = ROOT_DIR / "backend" / "fixtures"
GOLDEN_DIR = FIXTURES_DIR / "golden"


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_indian_number(val: Decimal | str | float) -> str:
    dec = Decimal(str(val))
    s = f"{dec:.2f}"
    int_part, dec_part = s.split(".")
    if len(int_part) <= 3:
        return f"{int_part}.{dec_part}"
    last3 = int_part[-3:]
    rest = int_part[:-3]
    chunks = []
    while len(rest) > 2:
        chunks.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        chunks.insert(0, rest)
    return f"{','.join(chunks)},{last3}.{dec_part}"


def num_to_words_indian(n: int) -> str:
    units = [
        "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
        "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen",
    ]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def convert_below_thousand(num: int) -> str:
        res = []
        if num >= 100:
            res.append(units[num // 100] + " Hundred")
            num %= 100
        if num >= 20:
            res.append(tens[num // 10])
            num %= 10
        if num > 0:
            res.append(units[num])
        return " ".join(res)

    if n == 0:
        return "Zero"

    parts = []
    crore = n // 10000000
    n %= 10000000
    lakh = n // 100000
    n %= 100000
    thousand = n // 1000
    n %= 1000
    rem = n

    if crore:
        parts.append(convert_below_thousand(crore) + " Crore")
    if lakh:
        parts.append(convert_below_thousand(lakh) + " Lakh")
    if thousand:
        parts.append(convert_below_thousand(thousand) + " Thousand")
    if rem:
        parts.append(convert_below_thousand(rem))

    return " ".join(parts).strip()


def amount_to_words(amt: Decimal) -> str:
    rupees = int(amt)
    paise = int(round((amt - Decimal(rupees)) * 100))
    words = "Rupees " + num_to_words_indian(rupees)
    if paise > 0:
        words += f" and {num_to_words_indian(paise)} Paise"
    words += " Only"
    return words


def format_raw_date(dt_str: str | None, layout: str) -> str | None:
    if not dt_str:
        return None
    d = parse_date(dt_str)
    if not d:
        return None
    if layout == "classic":
        return d.strftime("%d/%m/%Y")
    elif layout == "modern":
        return d.strftime("%d %b %Y")
    elif layout == "compact":
        return d.strftime("%d-%b-%y")
    return dt_str


# ---------------------------------------------------------------------------
# PDF Layout Builder
# ---------------------------------------------------------------------------

def build_pdf_story(fix: dict, layout: str) -> list:
    """Build the flowables for an invoice fixture according to its layout."""
    styles = getSampleStyleSheet()

    # Font sizing based on layout
    base_font_size = 7.5 if layout == "compact" else 8.5
    title_font_size = 13 if layout == "compact" else 15
    line_leading = base_font_size + 2.5

    body_style = ParagraphStyle(
        "InvoiceBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=base_font_size,
        leading=line_leading,
        textColor=colors.HexColor("#222222"),
    )
    body_bold = ParagraphStyle(
        "InvoiceBodyBold",
        parent=body_style,
        fontName="Helvetica-Bold",
    )
    right_style = ParagraphStyle(
        "InvoiceRight",
        parent=body_style,
        alignment=2,
    )
    right_bold = ParagraphStyle(
        "InvoiceRightBold",
        parent=body_bold,
        alignment=2,
    )
    title_style = ParagraphStyle(
        "InvoiceTitle",
        fontName="Helvetica-Bold",
        fontSize=title_font_size,
        leading=title_font_size + 3,
        alignment=1,
        textColor=colors.HexColor("#111111"),
    )

    story = []
    printable_width = 180 * mm

    # 1. Header: Vendor Block & Title & Meta
    is_f09 = fix.get("fixture_id") == "F09"
    title_text = "INVOICE" if is_f09 else "TAX INVOICE"
    story.append(Paragraph(title_text, title_style))
    story.append(Spacer(1, 4 * mm))

    # Vendor block
    v = fix["vendor"]
    vendor_lines = [
        f"<b>{v['printed_name']}</b>",
        v["address"],
        f"<b>GSTIN:</b> {v['gstin']}",
        f"<b>Email:</b> {v['email']}",
    ]
    vendor_p = Paragraph("<br/>".join(vendor_lines), body_style)

    # Meta block
    meta_lines = []
    if is_f09:
        meta_lines.append("<b>Invoice No.:</b> ____________________")
        meta_lines.append("<b>Invoice Date:</b> ____________________")
    else:
        inv_no = fix.get("invoice_number", "—")
        raw_date = format_raw_date(fix.get("invoice_date"), layout) or "—"
        meta_lines.append(f"<b>Invoice No.:</b> {inv_no}")
        meta_lines.append(f"<b>Invoice Date:</b> {raw_date}")

    if fix.get("po_number_printed"):
        meta_lines.append(f"<b>PO No.:</b> {fix['po_number_printed']}")
    elif fix.get("po_reference_text"):
        meta_lines.append(f"<b>Order Ref:</b> {fix['po_reference_text']}")

    meta_p = Paragraph("<br/>".join(meta_lines), right_style if layout != "classic" else body_style)

    # Place vendor & meta in a 2-column table
    if layout == "classic":
        header_table = Table([[vendor_p, meta_p]], colWidths=[105 * mm, 75 * mm])
        header_table.setStyle(
            TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#444444")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
                ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
                ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ])
        )
        story.append(header_table)
    else:
        header_table = Table([[vendor_p, meta_p]], colWidths=[110 * mm, 70 * mm])
        header_table.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ])
        )
        story.append(header_table)
        if layout == "modern":
            story.append(Spacer(1, 2 * mm))
            story.append(
                HRFlowable(
                    width="100%", thickness=2, color=colors.HexColor("#222222"), spaceAfter=2 * mm
                )
            )

    story.append(Spacer(1, 4 * mm))

    # 2. Bill To Block
    b = fix["buyer"]
    buyer_lines = [
        "<b>Bill To:</b>",
        f"<b>{b['name']}</b>",
        b["address"],
        f"<b>GSTIN:</b> {b['gstin']}",
    ]
    buyer_p = Paragraph("<br/>".join(buyer_lines), body_style)
    buyer_table = Table([[buyer_p]], colWidths=[printable_width])
    buyer_table.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8F9FA")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ])
    )
    story.append(buyer_table)
    story.append(Spacer(1, 4 * mm))

    # 3. Line Items Table
    col_widths = [8 * mm, 62 * mm, 18 * mm, 15 * mm, 15 * mm, 22 * mm, 15 * mm, 25 * mm]
    headers = [
        Paragraph("<b>#</b>", body_style),
        Paragraph("<b>Description</b>", body_style),
        Paragraph("<b>HSN/SAC</b>", body_style),
        Paragraph("<b>Qty</b>", right_bold),
        Paragraph("<b>UOM</b>", body_style),
        Paragraph("<b>Rate (Rs.)</b>", right_bold),
        Paragraph("<b>GST %</b>", right_bold),
        Paragraph("<b>Amount (Rs.)</b>", right_bold),
    ]
    table_data = [headers]

    for idx, item in enumerate(fix.get("line_items", []), start=1):
        row = [
            Paragraph(str(idx), body_style),
            Paragraph(item["description"], body_style),
            Paragraph(item.get("hsn_sac") or "—", body_style),
            Paragraph(str(item["quantity"]), right_style),
            Paragraph(item.get("uom") or "NOS", body_style),
            Paragraph(format_indian_number(item["unit_price"]), right_style),
            Paragraph(f"{Decimal(str(item['tax_rate_percent'])):.0f}%", right_style),
            Paragraph(format_indian_number(item["line_amount"]), right_style),
        ]
        table_data.append(row)

    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    t_style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2 * mm if layout != "compact" else 1.2 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm if layout != "compact" else 1.2 * mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 1.5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1.5 * mm),
    ]

    if layout == "classic":
        t_style.extend([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#444444")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAEAEA")),
        ])
    elif layout == "modern":
        t_style.extend([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEEE")),
            ("LINEABOVE", (0, 0), (-1, 0), 1.5, colors.HexColor("#222222")),
            ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.HexColor("#222222")),
            ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ])
    elif layout == "compact":
        t_style.extend([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#888888")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F0F0F0")),
        ])

    table.setStyle(TableStyle(t_style))
    story.append(table)
    story.append(Spacer(1, 4 * mm))

    # 4. Totals Block (Right-aligned table)
    totals = fix["printed_totals"]
    is_tax_incl = fix.get("amounts_include_tax", False)
    fid = fix.get("fixture_id")

    totals_rows = []
    if is_tax_incl:
        totals_rows.append([
            Paragraph("Total (inclusive of GST)", body_style),
            Paragraph(f"Rs. {format_indian_number(totals['subtotal'])}", right_style),
        ])
        totals_rows.append([
            Paragraph(
                "<font color='#555555'><i>"
                "Includes CGST 2.5% Rs. 1,087.50 and SGST 2.5% Rs. 1,087.50"
                "</i></font>",
                body_style,
            ),
            Paragraph("", right_style),
        ])
    else:
        totals_rows.append([
            Paragraph("Taxable Value", body_style),
            Paragraph(f"Rs. {format_indian_number(totals['net_taxable_value'])}", right_style),
        ])

        # Tax rows
        if fid == "F03":  # Mixed rates
            totals_rows.append([
                Paragraph("CGST", body_style),
                Paragraph(f"Rs. {format_indian_number(totals['cgst'])}", right_style),
            ])
            totals_rows.append([
                Paragraph("SGST", body_style),
                Paragraph(f"Rs. {format_indian_number(totals['sgst'])}", right_style),
            ])
        else:
            cgst = Decimal(str(totals.get("cgst", "0.00")))
            sgst = Decimal(str(totals.get("sgst", "0.00")))
            igst = Decimal(str(totals.get("igst", "0.00")))

            if igst > 0:
                first_line_tax = fix.get("line_items", [{}])[0].get("tax_rate_percent", "18")
                totals_rows.append([
                    Paragraph(f"IGST @ {first_line_tax}%", body_style),
                    Paragraph(f"Rs. {format_indian_number(igst)}", right_style),
                ])
            else:
                first_line_tax = Decimal(str(fix.get("line_items", [{}])[0].get("tax_rate_percent", "18")))
                half_rate = f"{first_line_tax / 2:.1f}".rstrip("0").rstrip(".")
                totals_rows.append([
                    Paragraph(f"CGST @ {half_rate}%", body_style),
                    Paragraph(f"Rs. {format_indian_number(cgst)}", right_style),
                ])
                totals_rows.append([
                    Paragraph(f"SGST @ {half_rate}%", body_style),
                    Paragraph(f"Rs. {format_indian_number(sgst)}", right_style),
                ])

        totals_rows.append([
            Paragraph("Total Tax", body_style),
            Paragraph(f"Rs. {format_indian_number(totals['total_tax'])}", right_style),
        ])

    totals_rows.append([
        Paragraph("<b>Grand Total</b>", body_bold),
        Paragraph(f"<b>Rs. {format_indian_number(totals['grand_total'])}</b>", right_bold),
    ])

    totals_table = Table(totals_rows, colWidths=[90 * mm, 40 * mm], hAlign="RIGHT")
    totals_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 1.2 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2 * mm),
            ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#222222")),
            ("LINEBELOW", (0, -1), (-1, -1), 1.5, colors.HexColor("#222222")),
        ])
    )
    story.append(totals_table)
    story.append(Spacer(1, 3 * mm))

    # 5. Amount in Words
    g_total = Decimal(str(totals["grand_total"]))
    words_text = f"<b>Amount in Words:</b> {amount_to_words(g_total)}"
    story.append(Paragraph(words_text, body_style))
    story.append(Spacer(1, 3 * mm))

    # 6. Bank Details Box (if present)
    if fix.get("bank_details_printed"):
        b_info = fix["bank_details_printed"]
        bank_lines = [
            "<b>Bank Details for Remittance:</b>",
            f"Bank: {b_info['bank_name']} &nbsp;|&nbsp; A/c Name: {b_info['account_name']}",
            f"A/c No.: {b_info['account_number']} &nbsp;|&nbsp; IFSC: {b_info['ifsc']}",
        ]
        bank_p = Paragraph("<br/>".join(bank_lines), body_style)
        bank_table = Table([[bank_p]], colWidths=[printable_width])
        bank_table.setStyle(
            TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#777777")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F9F9F9")),
                ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
                ("LEFTPADDING", (0, 0), (-1, -1), 2.5 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ])
        )
        story.append(bank_table)
        story.append(Spacer(1, 3 * mm))

    # 7. Footer Notes (bordered box, bold for F05)
    if fix.get("footer_notes"):
        note_text = fix["footer_notes"]
        if fid == "F05":
            note_content = f"<b>{note_text}</b>"
        else:
            note_content = note_text
        note_p = Paragraph(f"<b>Note:</b> {note_content}", body_style)
        note_table = Table([[note_p]], colWidths=[printable_width])
        box_color = colors.HexColor("#E53E3E") if fid == "F05" else colors.HexColor("#999999")
        bg_color = colors.HexColor("#FFF5F5") if fid == "F05" else colors.HexColor("#FAFAFA")
        note_table.setStyle(
            TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.75, box_color),
                ("BACKGROUND", (0, 0), (-1, -1), bg_color),
                ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
                ("LEFTPADDING", (0, 0), (-1, -1), 2.5 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ])
        )
        story.append(note_table)
        story.append(Spacer(1, 3 * mm))

    # 8. Authorised Signatory Block
    sig_lines = [
        f"<b>For {v['printed_name']}</b>",
        "<br/><br/><br/>",
        "Authorised Signatory",
    ]
    sig_p = Paragraph("<br/>".join(sig_lines), right_style)
    sig_table = Table([[sig_p]], colWidths=[printable_width])
    sig_table.setStyle(
        TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])
    )
    story.append(sig_table)

    return story


def generate_single_pdf(fix: dict, out_pdf_path: Path):
    """Render deterministic PDF for a fixture."""
    layout = fix.get("layout", "classic")
    story = build_pdf_story(fix, layout)

    temp_vec_path = out_pdf_path if not fix.get("scanned") else out_pdf_path.with_suffix(".tmp.pdf")

    doc = SimpleDocTemplate(
        str(temp_vec_path),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    # Set metadata for deterministic output
    def on_first_page(canvas, _doc):
        canvas.setAuthor("Kestrel AP")
        canvas.setCreator("Kestrel AP Invoice Generator")
        canvas.setTitle(fix.get("title", "Tax Invoice"))
        canvas.setSubject("AP Invoice Fixture")

    doc.build(story, onFirstPage=on_first_page)

    if fix.get("scanned"):
        # Apply scanned effect per doc 05 §5.3
        logger.info("Applying scanned effect to %s...", fix["fixture_id"])
        vec_doc = pymupdf.open(str(temp_vec_path))
        page = vec_doc[0]
        pix = page.get_pixmap(dpi=200, colorspace=pymupdf.csGRAY)
        img = Image.frombytes("L", (pix.width, pix.height), pix.samples)

        # Rotate +0.6 deg
        img = img.rotate(0.6, resample=Image.Resampling.BICUBIC, expand=False, fillcolor=255)

        # Gaussian noise sigma = 6
        np.random.seed(42)
        arr = np.array(img, dtype=float)
        noise = np.random.normal(0, 6, arr.shape)
        arr = np.clip(arr + noise, 0, 255)

        # Paper tint multiply by 247/255
        arr = np.clip(arr * (247.0 / 255.0), 0, 255).astype(np.uint8)
        img = Image.fromarray(arr, mode="L")

        # Blur radius = 0.4
        img = img.filter(ImageFilter.GaussianBlur(radius=0.4))

        temp_jpg = out_pdf_path.with_suffix(".scanned.jpg")
        img.save(str(temp_jpg), "JPEG", quality=82)

        # Insert into new PDF with zero text layer
        scanned_doc = pymupdf.open()
        new_page = scanned_doc.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(new_page.rect, filename=str(temp_jpg))
        scanned_doc.save(str(out_pdf_path))

        vec_doc.close()
        scanned_doc.close()

        if temp_vec_path.exists():
            temp_vec_path.unlink()
        if temp_jpg.exists():
            temp_jpg.unlink()

        # Validate that output has no text layer
        final_doc = pymupdf.open(str(out_pdf_path))
        extracted_text = final_doc[0].get_text().strip()
        final_doc.close()
        assert len(extracted_text) == 0, (
            f"Expected 0 text chars for scanned fixture {fix['fixture_id']}, got {len(extracted_text)}"
        )
        logger.info("Scanned fixture %s verified: 0 text chars.", fix["fixture_id"])


def generate_golden_json(fix: dict, out_json_path: Path):
    """Write golden extraction ExtractedInvoice JSON."""
    fid = fix["fixture_id"]
    layout = fix.get("layout", "classic")
    raw_date = format_raw_date(fix.get("invoice_date"), layout)

    lines = []
    for l_item in fix.get("line_items", []):
        qty = Decimal(str(l_item["quantity"])) if l_item.get("quantity") is not None else None
        u_price = Decimal(str(l_item["unit_price"])) if l_item.get("unit_price") is not None else None
        t_rate = (
            Decimal(str(l_item["tax_rate_percent"]))
            if l_item.get("tax_rate_percent") is not None
            else None
        )
        l_amt = Decimal(str(l_item["line_amount"])) if l_item.get("line_amount") is not None else None

        lines.append(
            ExtractedLine(
                description=l_item["description"],
                hsn_sac=l_item.get("hsn_sac"),
                quantity=qty,
                uom=l_item.get("uom"),
                unit_price=u_price,
                tax_rate_percent=t_rate,
                line_amount=l_amt,
            )
        )

    totals = fix.get("printed_totals", {})
    tax = TaxBreakdown(
        cgst=Decimal(str(totals["cgst"])) if totals.get("cgst") is not None else None,
        sgst=Decimal(str(totals["sgst"])) if totals.get("sgst") is not None else None,
        igst=Decimal(str(totals["igst"])) if totals.get("igst") is not None else None,
    )

    bank = None
    if fix.get("bank_details_printed"):
        b = fix["bank_details_printed"]
        bank = BankDetails(
            bank_name=b.get("bank_name"),
            ifsc=b.get("ifsc"),
            account_number=b.get("account_number"),
            account_name=b.get("account_name"),
        )

    conf = {
        k: 0.99
        for k in [
            "vendor_name",
            "vendor_gstin",
            "invoice_number",
            "invoice_date",
            "grand_total",
            "po_number",
            "line_items",
        ]
    }

    # Special golden handling per doc 05 §5.4:
    # F09 has invoice_number=null, invoice_date=null, raw_date=null
    # F03 po_number=null, po_reference_text="As per your order dated 02-Nov-2026"
    inv_num = None if fid == "F09" else fix.get("invoice_number")
    inv_date = None if fid == "F09" else fix.get("invoice_date")
    inv_raw_date = None if fid == "F09" else raw_date
    po_num = None if fid == "F03" else fix.get("po_number_printed")
    po_ref = "As per your order dated 02-Nov-2026" if fid == "F03" else fix.get("po_reference_text")

    sub_tot = Decimal(str(totals["subtotal"])) if totals.get("subtotal") is not None else None
    tot_tax = Decimal(str(totals["total_tax"])) if totals.get("total_tax") is not None else None
    gr_tot = Decimal(str(totals["grand_total"])) if totals.get("grand_total") is not None else None

    ext = ExtractedInvoice(
        vendor_name=fix["vendor"].get("printed_name"),
        vendor_gstin=fix["vendor"].get("gstin"),
        vendor_address=fix["vendor"].get("address"),
        buyer_name=fix["buyer"].get("name"),
        buyer_gstin=fix["buyer"].get("gstin"),
        invoice_number=inv_num,
        invoice_date=inv_date,
        invoice_date_raw=inv_raw_date,
        currency="INR",
        po_number=po_num,
        po_reference_text=po_ref,
        amounts_include_tax=fix.get("amounts_include_tax", False),
        line_items=lines,
        subtotal=sub_tot,
        tax=tax,
        total_tax=tot_tax,
        grand_total=gr_tot,
        bank_details=bank,
        notes=fix.get("footer_notes"),
        field_confidence=conf,
        warnings=[],
    )

    with open(out_json_path, "w", encoding="utf-8") as f:
        # Serialise model to dict and write JSON
        f.write(ext.model_dump_json(indent=2))


def render_png_preview(pdf_path: Path, out_png_path: Path, dpi: int = 150):
    """Render page 1 of a PDF to PNG for visual inspection."""
    doc = pymupdf.open(str(pdf_path))
    page = doc[0]
    pix = page.get_pixmap(dpi=dpi)
    pix.save(str(out_png_path))
    doc.close()


def main():
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    with open(SEED_DATA_DIR / "fixtures.json", encoding="utf-8") as f:
        fixtures_data = json.load(f)

    logger.info("Generating 9 invoice PDFs and golden JSON files...")
    for fix in fixtures_data:
        fid = fix["fixture_id"]
        fname = fix["filename"]
        pdf_path = FIXTURES_DIR / fname
        golden_path = GOLDEN_DIR / f"{fid}.json"

        logger.info("Building %s (%s)...", fid, fname)
        generate_single_pdf(fix, pdf_path)
        generate_golden_json(fix, golden_path)

        # Generate PNG preview for inspection
        png_path = FIXTURES_DIR / f"{fid}_preview.png"
        render_png_preview(pdf_path, png_path)

    logger.info("All 9 invoice fixtures and golden JSONs generated successfully.")


if __name__ == "__main__":
    main()
