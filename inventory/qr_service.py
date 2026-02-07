"""
QR Code generation service for products.
"""
import qrcode
import io
import base64
from django.http import HttpResponse


class QRCodeService:
    """Service for generating QR codes for products."""
    
    @staticmethod
    def generate_qr_image(data: str, size: int = 200):
        """
        Generate a QR code image and return as bytes.
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Resize if needed
        img = img.resize((size, size))
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def generate_qr_base64(data: str, size: int = 200) -> str:
        """
        Generate a QR code and return as base64 string for embedding in HTML.
        """
        buffer = QRCodeService.generate_qr_image(data, size)
        b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{b64}"
    
    @staticmethod
    def generate_qr_response(data: str, filename: str = "qrcode.png"):
        """
        Generate a QR code and return as HTTP response for download.
        """
        buffer = QRCodeService.generate_qr_image(data)
        response = HttpResponse(buffer.getvalue(), content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
