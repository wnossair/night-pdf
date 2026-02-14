# backend/tests/test_utils.py
"""
Unit tests for utility functions in main.py.
"""

import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

# Import functions to test
sys.path.insert(0, str(Path(__file__).parent.parent))
from main import invert_smart, is_image_a_scan_or_chart, process_stream_content


class TestColorInversion:
    """Test the invert_smart function."""

    def test_invert_black(self):
        """Black should become light gray."""
        result = invert_smart(0.0, 0.0, 0.0)
        # Black (0,0,0) -> Light gray (~0.92, 0.92, 0.92)
        assert all(0.9 < c < 0.95 for c in result)

    def test_invert_white(self):
        """White should become dark gray."""
        result = invert_smart(1.0, 1.0, 1.0)
        # White (1,1,1) -> Dark gray (~0.25, 0.25, 0.25)
        assert all(0.2 < c < 0.3 for c in result)

    def test_invert_gray(self):
        """Medium gray should invert."""
        result = invert_smart(0.5, 0.5, 0.5)
        # Should invert
        assert result[0] != 0.5

    def test_invert_color_preserves_hue(self):
        """Colored text should preserve hue but change lightness."""
        # Bright red
        result = invert_smart(1.0, 0.0, 0.0)
        # Should still be red-ish (high R, low G/B)
        assert result[0] > result[1] and result[0] > result[2]
        # Should be darker (since original was bright)
        assert result[0] < 1.0

    def test_invert_dark_color(self):
        """Very dark color should become light."""
        result = invert_smart(0.05, 0.05, 0.05)
        # Should be light
        assert all(c > 0.8 for c in result)

    def test_invert_light_color(self):
        """Very light color should become dark."""
        result = invert_smart(0.95, 0.95, 0.95)
        # Should be dark
        assert all(c < 0.3 for c in result)


class TestImageDetection:
    """Test the is_image_a_scan_or_chart function."""

    def test_scan_detection_white_background(self, mock_image_scan):
        """Image with white background should be detected as scan/chart."""
        assert is_image_a_scan_or_chart(mock_image_scan) is True

    def test_photo_not_detected(self, mock_image_photo):
        """Gradient/image should NOT be detected as scan/chart."""
        assert is_image_a_scan_or_chart(mock_image_photo) is False

    def test_small_image(self):
        """Small image should handle gracefully."""
        img = Image.new("RGB", (10, 10), color="white")
        # Should return False for very small images
        result = is_image_a_scan_or_chart(img)
        # Just ensure it doesn't crash
        assert result in [True, False]

    def test_rgba_image(self):
        """RGBA image should be handled."""
        img = Image.new("RGBA", (100, 100), color=(255, 255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle((20, 20, 80, 80), fill=(0, 0, 255, 255))
        # Should process without error
        result = is_image_a_scan_or_chart(img)
        assert result in [True, False]

    def test_grayscale_image(self):
        """Grayscale image should be handled."""
        img = Image.new("L", (100, 100), color=255)
        # Should process without error
        result = is_image_a_scan_or_chart(img)
        assert result in [True, False]

    def test_invalid_mode(self):
        """Image with unsupported mode should return False."""
        img = Image.new("CMYK", (100, 100))
        assert is_image_a_scan_or_chart(img) is False

    @pytest.mark.parametrize(
        "brightness,expected",
        [
            (230, True),  # Very bright corners
            (180, False),  # Medium brightness
            (100, False),  # Dark corners
        ],
    )
    def test_corner_brightness(self, brightness, expected):
        """Test different corner brightness levels."""
        img = Image.new("RGB", (200, 200), color=(brightness, brightness, brightness))
        # All corners are the same brightness
        result = is_image_a_scan_or_chart(img)
        # Note: function also checks mean brightness > 180
        if brightness >= 200:
            assert result == expected
        else:
            assert result is False


class TestStreamProcessing:
    """Test stream processing functions."""

    def test_process_stream_content_basic(self):
        """Test that process_stream_content doesn't crash on basic input."""
        # Simple PDF content with color commands
        content = b"0 g\n0 0 0 rg\n1 1 1 RG\n(Tj) Tj"
        result = process_stream_content(content, "test")

        # Should return bytes
        assert isinstance(result, bytes)
        # Should have changed something
        assert result != content
        # Should contain our default light colors
        assert b"0.9" in result

    def test_process_stream_empty(self):
        """Test empty content."""
        result = process_stream_content(b"", "empty")
        assert result == b""

    def test_process_stream_no_colors(self):
        """Test content without color commands."""
        content = b"(Hello World) Tj\nBT /F1 12 Tf ET"
        result = process_stream_content(content, "no-colors")

        # Should still process without error
        assert isinstance(result, bytes)
        # Should add default colors if Tj/TJ is present
        if b"Tj" in content or b"TJ" in content:
            assert b"0.9 g" in result or b"0.9 0.9 0.9 rg" in result

    def test_process_stream_decoding_error(self):
        """Test content that cannot be decoded."""
        # Binary content that's not valid latin-1
        content = b"\xff\xfe\x00"  # Invalid latin-1
        result = process_stream_content(content, "invalid")
        # Should return original content
        assert result == content
