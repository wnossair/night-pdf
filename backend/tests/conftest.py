# backend/tests/conftest.py
"""
Pytest fixtures for PDF Night Mode tests.
"""

import sys
import tempfile
from pathlib import Path

import pytest
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient

# Import the main app
sys.path.insert(0, str(Path(__file__).parent.parent))
from main import app


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_pdf_bytes():
    """Create a simple test PDF with text and images."""
    doc = fitz.open()

    # Page 1: Text
    page = doc.new_page()
    page.insert_text((50, 50), "Hello World", fontsize=12, color=(0, 0, 0))
    page.insert_text((50, 70), "This is black text", fontsize=12, color=(0, 0, 0))
    page.insert_text((50, 90), "This is red text", fontsize=12, color=(1, 0, 0))
    page.insert_text((50, 110), "This is gray text", fontsize=12, color=(0.5, 0.5, 0.5))

    # Page 2: Images
    page2 = doc.new_page()

    # Create a test image (bright chart-like image)
    img = Image.new("RGB", (100, 100), color="white")
    draw = ImageDraw.Draw(img)
    draw.rectangle((20, 20, 80, 80), fill="black", outline="red")
    draw.text((30, 40), "TEST", fill="blue")

    img_bytes = tempfile.SpooledTemporaryFile(max_size=1000)
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    # Insert image
    rect = fitz.Rect(50, 50, 150, 150)
    page2.insert_image(rect, stream=img_bytes.read())
    img_bytes.close()

    # Save to bytes
    pdf_bytes = doc.write()
    doc.close()

    return pdf_bytes


@pytest.fixture
def sample_pdf_file(sample_pdf_bytes):
    """Create a temporary PDF file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(sample_pdf_bytes)
        f.flush()
        temp_path = Path(f.name)
    yield temp_path
    # Cleanup
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def dark_background_color():
    """Return the dark background color used in the app."""
    return (18 / 255, 18 / 255, 18 / 255)


@pytest.fixture
def mock_image_scan():
    """Create a mock image that should be detected as a scan/chart."""
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))  # White background
    draw = ImageDraw.Draw(img)
    draw.rectangle((50, 50, 150, 150), fill=(0, 0, 255), outline=(255, 0, 0))
    draw.text((60, 80), "CHART", fill=(0, 0, 0))
    return img


@pytest.fixture
def mock_image_photo():
    """Create a mock image that should NOT be detected as a scan/chart."""
    # Create a gradient (more like a photo)
    img = Image.new("RGB", (200, 200))
    for x in range(200):
        for y in range(200):
            color = int((x + y) / 4)
            img.putpixel((x, y), (color, color, color))
    return img


@pytest.fixture(scope="session")
def test_data_dir():
    """Directory for test data files."""
    return Path(__file__).parent / "test_data"
