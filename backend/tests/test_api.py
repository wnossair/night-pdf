# backend/tests/test_api.py
"""
Tests for FastAPI endpoints.
"""

import fitz  # PyMuPDF
from unittest.mock import patch


class TestHealthEndpoint:
    """Test the health check endpoint."""

    def test_health_endpoint(self, client):
        """Health endpoint should return healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Platinum PDF Night Mode"
        assert "version" in data


class TestConvertEndpoint:
    """Test the PDF conversion endpoint."""

    def test_convert_no_file(self, client):
        """POST without file should return 422."""
        response = client.post("/convert")
        assert response.status_code == 422  # Validation error

    def test_convert_wrong_file_type(self, client):
        """POST with non-PDF file should return 400."""
        files = {"file": ("test.txt", b"not a pdf", "text/plain")}
        response = client.post("/convert", files=files)

        assert response.status_code == 400
        assert "must be a PDF" in response.json()["detail"]

    def test_convert_success(self, client, sample_pdf_bytes):
        """Successful conversion should return PDF."""
        files = {"file": ("test.pdf", sample_pdf_bytes, "application/pdf")}
        response = client.post("/convert", files=files)

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers["content-disposition"]
        assert response.headers["x-conversion-status"] == "success"

        # Should return valid PDF data
        pdf_data = response.content
        assert len(pdf_data) > 0
        assert pdf_data[:4] == b"%PDF"  # PDF magic number

    def test_convert_large_file(self, client):
        """Test with a larger PDF (simulated)."""
        # Create a larger PDF
        doc = fitz.open()
        for i in range(10):  # 10 pages
            page = doc.new_page()
            page.insert_text((50, 50), f"Page {i + 1}", fontsize=12)
        pdf_bytes = doc.write()
        doc.close()

        files = {"file": ("large.pdf", pdf_bytes, "application/pdf")}
        response = client.post("/convert", files=files)

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    @patch("main.process_stream_content")
    def test_convert_stream_processing(self, mock_process, client, sample_pdf_bytes):
        """Test that stream processing is called."""
        mock_process.return_value = b"processed"

        files = {"file": ("test.pdf", sample_pdf_bytes, "application/pdf")}
        response = client.post("/convert", files=files)

        assert response.status_code == 200
        # Our mock should have been called
        assert mock_process.called

    def test_convert_error_handling(self, client):
        """Test error handling during conversion."""
        # Mock fitz.open to raise an exception
        with patch("main.fitz.open", side_effect=Exception("Test error")):
            files = {"file": ("test.pdf", b"invalid pdf", "application/pdf")}
            response = client.post("/convert", files=files)

            assert response.status_code == 500
            assert "Conversion failed" in response.json()["detail"]

    def test_filename_handling(self, client, sample_pdf_bytes):
        """Test various filename formats."""
        test_cases = [
            ("document.pdf", "night_document.pdf"),
            ("my file.pdf", "night_my file.pdf"),
            ("DOC.PDF", "night_DOC.PDF"),
            ("noextension", "night_noextension.pdf"),
        ]

        for input_name, expected_name in test_cases:
            files = {"file": (input_name, sample_pdf_bytes, "application/pdf")}
            response = client.post("/convert", files=files)

            assert response.status_code == 200
            content_disp = response.headers["content-disposition"]
            assert expected_name in content_disp


class TestResponseHeaders:
    """Test response headers from conversion."""

    def test_response_headers(self, client, sample_pdf_bytes):
        """Check that all expected headers are present."""
        files = {"file": ("test.pdf", sample_pdf_bytes, "application/pdf")}
        response = client.post("/convert", files=files)

        headers = response.headers
        assert "content-disposition" in headers
        assert "content-type" in headers
        assert "x-conversion-status" in headers
        assert "x-original-filename" in headers
        assert "x-output-size" in headers

        # Headers should have reasonable values
        assert headers["content-type"] == "application/pdf"
        assert headers["x-conversion-status"] == "success"
        assert int(headers["x-output-size"]) > 0
