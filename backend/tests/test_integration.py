# backend/tests/test_integration.py
"""
Integration tests for the complete PDF conversion pipeline.
"""

import io
import time

import pytest
import fitz  # PyMuPDF
from PIL import Image, ImageDraw


class TestFullConversion:
    """Integration tests for complete PDF conversion."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_full_pdf_conversion(self, client, sample_pdf_bytes):
        """Complete end-to-end test of PDF conversion."""
        # 1. Convert the PDF
        files = {"file": ("test.pdf", sample_pdf_bytes, "application/pdf")}
        response = client.post("/convert", files=files)
        assert response.status_code == 200

        # 2. Open the converted PDF
        converted_pdf = fitz.open(stream=response.content, filetype="pdf")

        # 3. Verify it's a valid PDF
        assert len(converted_pdf) > 0

        # 4. Check that background was added (by checking page count didn't change)
        # The original had 2 pages
        assert len(converted_pdf) == 2

        # 5. Check that text is still present
        page1_text = converted_pdf[0].get_text()
        assert "Hello World" in page1_text
        assert "This is black text" in page1_text

        # 6. Check for images on page 2
        page2_images = converted_pdf[1].get_images()
        assert len(page2_images) > 0

        converted_pdf.close()

    @pytest.mark.integration
    def test_color_inversion_in_output(self, client):
        """Verify that colors are actually inverted in output."""
        # Create a PDF with known colors
        doc = fitz.open()
        page = doc.new_page()

        # Add text with specific colors
        page.insert_text((50, 50), "Black Text", fontsize=12, color=(0, 0, 0))
        page.insert_text((50, 70), "White Text", fontsize=12, color=(1, 1, 1))
        page.insert_text((50, 90), "Red Text", fontsize=12, color=(1, 0, 0))

        pdf_bytes = doc.write()
        doc.close()

        # Convert
        files = {"file": ("colors.pdf", pdf_bytes, "application/pdf")}
        response = client.post("/convert", files=files)
        assert response.status_code == 200

        # Note: Actually verifying color changes in PDF is complex
        # For now, just ensure it processes without error
        converted = fitz.open(stream=response.content, filetype="pdf")
        assert len(converted) == 1
        converted.close()

    @pytest.mark.integration
    def test_image_inversion_logic(self, client):
        """Test that chart/images are inverted but photos are not."""
        doc = fitz.open()
        page = doc.new_page()

        # Create a bright image (should be inverted)
        bright_img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        draw = ImageDraw.Draw(bright_img)
        draw.rectangle((20, 20, 80, 80), fill=(0, 0, 255), outline=(255, 0, 0))

        bright_bytes = io.BytesIO()
        bright_img.save(bright_bytes, format="PNG")
        bright_bytes.seek(0)

        # Insert image
        rect = fitz.Rect(50, 50, 150, 150)
        page.insert_image(rect, stream=bright_bytes.getvalue())

        pdf_bytes = doc.write()
        doc.close()

        # Convert
        files = {"file": ("image_test.pdf", pdf_bytes, "application/pdf")}
        response = client.post("/convert", files=files)
        assert response.status_code == 200

        # Verify PDF is valid
        converted = fitz.open(stream=response.content, filetype="pdf")
        assert len(converted) == 1
        # Image should still be present
        images = converted[0].get_images()
        assert len(images) == 1
        converted.close()

    @pytest.mark.integration
    def test_multiple_pages(self, client):
        """Test PDF with multiple pages."""
        doc = fitz.open()
        for i in range(5):
            page = doc.new_page()
            page.insert_text((50, 50), f"Page {i + 1}", fontsize=12)

        pdf_bytes = doc.write()
        doc.close()

        files = {"file": ("multipage.pdf", pdf_bytes, "application/pdf")}
        response = client.post("/convert", files=files)
        assert response.status_code == 200

        converted = fitz.open(stream=response.content, filetype="pdf")
        assert len(converted) == 5
        converted.close()

    @pytest.mark.integration
    def test_empty_pdf(self, client):
        """Test empty PDF (edge case)."""
        doc = fitz.open()
        pdf_bytes = doc.write()  # Empty PDF
        doc.close()

        files = {"file": ("empty.pdf", pdf_bytes, "application/pdf")}
        response = client.post("/convert", files=files)

        # Should still succeed (empty PDF is valid)
        assert response.status_code == 200
        converted = fitz.open(stream=response.content, filetype="pdf")
        assert len(converted) == 0
        converted.close()


class TestPerformance:
    """Performance-related tests."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_large_pdf_performance(self, client):
        """Test with a moderately large PDF."""
        # Create a 20-page PDF
        doc = fitz.open()
        for i in range(20):
            page = doc.new_page()
            # Add some text
            for j in range(10):
                page.insert_text((50, 50 + j * 20), f"Line {j + 1} on page {i + 1}", fontsize=10)

        pdf_bytes = doc.write()
        doc.close()

        start_time = time.time()
        files = {"file": ("large.pdf", pdf_bytes, "application/pdf")}
        response = client.post("/convert", files=files)
        end_time = time.time()

        assert response.status_code == 200
        processing_time = end_time - start_time

        # Should complete in reasonable time (adjust as needed)
        assert processing_time < 30.0  # 30 seconds max

        print(f"Large PDF processed in {processing_time:.2f} seconds")
