"""
UPI Payment Link & QR Code Generator.

Generates UPI deep links (upi://pay?...) and QR codes for settlement payments.
Format: upi://pay?pa={upi_id}&pn={name}&am={rupees.2f}&cu=INR&tn={note}
"""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from urllib.parse import quote


@dataclass
class UPIPayment:
    """Generated UPI payment details."""
    uri: str  # UPI deep link
    qr_base64: str  # Base64-encoded SVG QR code
    amount_rupees: str  # Formatted amount (e.g., "450.50")
    payee_name: str
    payee_upi_id: str
    note: str


def _paise_to_rupees(paise: int) -> str:
    """Convert paise to rupees string with 2 decimal places."""
    rupees = paise / 100
    return f"{rupees:.2f}"


def generate_upi_link(
    upi_id: str,
    payee_name: str,
    amount_paise: int,
    note: str = "SplitSmart settlement",
    currency: str = "INR",
) -> UPIPayment:
    """
    Generate a UPI deep link and QR code for a payment.

    Args:
        upi_id: Payee's UPI ID (e.g., "name@paytm")
        payee_name: Display name of the payee
        amount_paise: Amount in paise (e.g., 45050 for Rs 450.50)
        note: Transaction note
        currency: Currency code (default: INR)

    Returns:
        UPIPayment with URI and QR code
    """
    amount_rupees = _paise_to_rupees(amount_paise)

    # Build UPI URI
    uri = (
        f"upi://pay"
        f"?pa={quote(upi_id)}"
        f"&pn={quote(payee_name)}"
        f"&am={amount_rupees}"
        f"&cu={currency}"
        f"&tn={quote(note)}"
    )

    # Generate QR code
    qr_base64 = _generate_qr_base64(uri)

    return UPIPayment(
        uri=uri,
        qr_base64=qr_base64,
        amount_rupees=amount_rupees,
        payee_name=payee_name,
        payee_upi_id=upi_id,
        note=note,
    )


def _generate_qr_base64(data: str) -> str:
    """Generate a QR code as a base64-encoded SVG string."""
    try:
        import qrcode
        import qrcode.image.svg

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        # Generate SVG
        factory = qrcode.image.svg.SvgPathImage
        img = qr.make_image(image_factory=factory)

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer)
        svg_bytes = buffer.getvalue()

        return base64.b64encode(svg_bytes).decode("utf-8")

    except ImportError:
        # Fallback: return a placeholder if qrcode library isn't available
        placeholder_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">'
            '<rect width="200" height="200" fill="#f0f0f0"/>'
            '<text x="100" y="100" text-anchor="middle" font-size="14">'
            'QR Code</text></svg>'
        )
        return base64.b64encode(placeholder_svg.encode()).decode("utf-8")


def generate_settlement_link(
    debtor_name: str,
    creditor_name: str,
    creditor_upi_id: str,
    amount_paise: int,
    group_name: str = "",
) -> UPIPayment:
    """
    Convenience function to generate a UPI settlement link.

    Creates a descriptive note like "SplitSmart: Aryan → Priya (Goa Weekend Squad)"
    """
    note = f"SplitSmart: {debtor_name} → {creditor_name}"
    if group_name:
        note += f" ({group_name})"

    return generate_upi_link(
        upi_id=creditor_upi_id,
        payee_name=creditor_name,
        amount_paise=amount_paise,
        note=note,
    )
