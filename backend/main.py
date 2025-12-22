"""
Backend API for Platinum PDF Night Mode.
Enhanced with comprehensive logging and proper PDF syntax handling.
"""

import io
import re
import colorsys
import fitz  # PyMuPDF
from PIL import Image, ImageOps, ImageStat
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Platinum PDF Night Mode")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DARK_BG = (18 / 255, 18 / 255, 18 / 255)  # #121212


def invert_smart(r: float, g: float, b: float) -> tuple[float, float, float]:
    """
    Enhanced color inversion for optimal dark mode readability.
    """
    # Convert to HLS
    h, l, s = colorsys.rgb_to_hls(r, g, b)

    # For very dark colors (nearly black), make them light
    if l < 0.1:
        return (0.92, 0.92, 0.92)  # Light gray for readability

    # For very light colors (nearly white), make them dark but not too dark
    if l > 0.9:
        return (0.25, 0.25, 0.25)  # Medium-dark gray

    # For grayscale (low saturation)
    if s < 0.15:
        if l > 0.5:
            return (0.15, 0.15, 0.15)  # Light -> Dark
        else:
            return (0.85, 0.85, 0.85)  # Dark -> Light

    # For colored text, preserve hue but adjust lightness
    new_l = 1.0 - l

    # Ensure good contrast on dark background
    if new_l < 0.3:
        new_l = 0.3  # Minimum brightness for colored text
    elif new_l > 0.95:
        new_l = 0.95  # Maximum brightness

    return colorsys.hls_to_rgb(h, new_l, s)


def process_stream_content(content: bytes, context: str = "unknown") -> bytes:
    """
    Process PDF content stream to invert colors.
    Returns modified content bytes.
    """
    logger.info(f"Processing stream for {context} (length: {len(content)} bytes)")

    if not content:
        return content

    original_content = content
    changes_made = 0

    # Convert to string for easier regex processing (PDF content is ASCII/UTF-8)
    try:
        content_str = content.decode("latin-1")
    except:
        logger.warning(f"Could not decode content for {context}, skipping")
        return content

    # Helper function to process color matches
    def process_color_match(match):
        nonlocal changes_made
        full_match = match.group(0)

        # Extract numbers and operator
        try:
            # Split the match into parts
            parts = full_match.strip().split()
            if len(parts) < 2:
                return full_match

            operator = parts[-1]
            numbers = parts[:-1]

            logger.debug(f"Found color command: {full_match} (operator: {operator}, numbers: {len(numbers)})")

            # Parse numbers
            try:
                num_values = [float(n) for n in numbers]
            except ValueError:
                logger.warning(f"Could not parse numbers in: {full_match}")
                return full_match

            # Process based on operator and number count
            new_numbers = []

            if operator.lower() in ["g", "rg", "k"]:
                if operator.lower() == "g" and len(num_values) == 1:
                    # Grayscale
                    val = num_values[0]
                    new_val = 0.9 if val < 0.5 else 0.15
                    new_numbers = [f"{new_val:.3f}"]
                    changes_made += 1

                elif operator.lower() == "rg" and len(num_values) == 3:
                    # RGB
                    r, g, b = num_values
                    nr, ng, nb = invert_smart(r, g, b)
                    new_numbers = [f"{nr:.3f}", f"{ng:.3f}", f"{nb:.3f}"]
                    changes_made += 1

                elif operator.lower() == "k" and len(num_values) == 4:
                    # CMYK
                    c, m, y, k = num_values
                    if k > 0.5:
                        new_c, new_m, new_y, new_k = c * 0.2, m * 0.2, y * 0.2, 0.0
                    else:
                        new_c, new_m, new_y, new_k = c * 0.3, m * 0.3, y * 0.3, 0.8
                    new_numbers = [
                        f"{new_c:.3f}",
                        f"{new_m:.3f}",
                        f"{new_y:.3f}",
                        f"{new_k:.3f}",
                    ]
                    changes_made += 1
                else:
                    return full_match
            else:
                return full_match

            # Reconstruct the command
            new_command = " ".join(new_numbers) + " " + operator
            logger.debug(f"Replaced: {full_match} -> {new_command}")
            return new_command

        except Exception as e:
            logger.error(f"Error processing color match '{full_match}': {e}")
            return full_match

    # Pattern to match color commands
    # Matches: number(s) followed by color operator
    color_pattern = r"(\d+(?:\.\d*)?|\.\d+)(?:\s+(\d+(?:\.\d*)?|\.\d+))?(?:\s+(\d+(?:\.\d*)?|\.\d+))?(?:\s+(\d+(?:\.\d*)?|\.\d+))?\s+(g|G|rg|RG|k|K)"

    # Process all color commands
    processed_str = re.sub(color_pattern, process_color_match, content_str)

    # Also replace common black/white defaults
    # Common black text patterns
    black_patterns = [
        (r"\b0\s+g\b", "0.9 g"),
        (r"\b0\s+G\b", "0.9 G"),
        (r"\b0\s+0\s+0\s+rg\b", "0.9 0.9 0.9 rg"),
        (r"\b0\s+0\s+0\s+RG\b", "0.9 0.9 0.9 RG"),
        (r"\b1\s+g\b", "0.15 g"),  # White -> dark gray
        (r"\b1\s+G\b", "0.15 G"),
        (r"\b1\s+1\s+1\s+rg\b", "0.25 0.25 0.25 rg"),
        (r"\b1\s+1\s+1\s+RG\b", "0.25 0.25 0.25 RG"),
    ]

    for pattern, replacement in black_patterns:
        if re.search(pattern, processed_str):
            processed_str = re.sub(pattern, replacement, processed_str)
            changes_made += 1

    # Add default color state at the beginning if we found any text rendering commands
    if "Tj" in processed_str or "TJ" in processed_str:
        # Prepend default color commands
        default_colors = "0.9 g 0.9 G 0.9 0.9 0.9 rg 0.9 0.9 0.9 RG "
        if not processed_str.startswith(default_colors):
            processed_str = default_colors + processed_str
            changes_made += 1
            logger.debug("Added default color commands to stream")

    if changes_made > 0:
        logger.info(f"Made {changes_made} color changes in {context}")

    # Convert back to bytes
    return processed_str.encode("latin-1")


def process_xobject_recursively(doc, xref, processed_xrefs, depth=0):
    """
    Recursively process XObjects.
    """
    if xref in processed_xrefs or xref == 0:
        return

    processed_xrefs.add(xref)

    try:
        # Get object type
        obj_type = doc.xref_get_key(xref, "Type")
        subtype = doc.xref_get_key(xref, "Subtype")

        if subtype and subtype[1] == "/Form":
            logger.debug(f"{'  ' * depth}Processing Form XObject {xref}")

            # Get and process the stream
            stream = doc.xref_stream(xref)
            if stream:
                new_stream = process_stream_content(stream, f"XObject {xref}")
                if new_stream != stream:
                    doc.update_stream(xref, new_stream)
                    logger.debug(f"{'  ' * depth}Updated XObject {xref} stream")

            # Check for nested XObjects in Resources
            try:
                resources_xref = doc.xref_get_key(xref, "Resources")
                if resources_xref and resources_xref[0] == "dict":
                    # Parse resources dict to find XObjects
                    resources = doc.xref_object(xref, compressed=True)
                    if resources:
                        # Look for XObject references
                        xobj_match = re.search(r"/XObject\s*<<([^>]+)>>", resources)
                        if xobj_match:
                            xobj_block = xobj_match.group(1)
                            # Find object references
                            obj_refs = re.findall(r"/(\w+)\s+(\d+)\s+0\s+R", xobj_block)
                            for name, obj_xref in obj_refs:
                                process_xobject_recursively(doc, int(obj_xref), processed_xrefs, depth + 1)
            except Exception as e:
                logger.debug(f"{'  ' * depth}Could not process resources for XObject {xref}: {e}")

    except Exception as e:
        logger.warning(f"Error processing XObject {xref}: {e}")


def is_image_a_scan_or_chart(pil_image: Image.Image) -> bool:
    """Heuristic to detect charts/scans vs photos."""
    if pil_image.mode not in ["RGB", "L", "RGBA"]:
        return False

    try:
        # Convert to grayscale for analysis
        if pil_image.mode == "RGBA":
            gray_img = pil_image.convert("L")
        else:
            gray_img = pil_image.convert("L")

        stat = ImageStat.Stat(gray_img)
        mean_brightness = stat.mean[0]

        w, h = pil_image.size
        if w == 0 or h == 0:
            return False

        # Sample corner pixels
        corners = []
        for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
            if x < w and y < h:
                val = gray_img.getpixel((x, y))
                corners.append(val)

        if not corners:
            return False

        avg_corner_brightness = sum(corners) / len(corners)

        # Charts/scans typically have bright backgrounds and high average brightness
        if avg_corner_brightness > 200 and mean_brightness > 180:
            return True

        return False
    except Exception as e:
        logger.warning(f"Error analyzing image: {e}")
        return False


def process_images_in_doc(doc):
    """Iterates and inverts specific images."""
    processed_xrefs = set()

    for page_num, page in enumerate(doc):
        try:
            image_list = page.get_images()
            if image_list:
                logger.info(f"Page {page_num + 1} has {len(image_list)} images")

            for img_index, img in enumerate(image_list):
                xref = img[0]
                if xref in processed_xrefs:
                    continue

                processed_xrefs.add(xref)

                try:
                    base_image = doc.extract_image(xref)
                    if not base_image or "image" not in base_image:
                        continue

                    logger.debug(f"Processing image {xref} on page {page_num + 1}")

                    pil_image = Image.open(io.BytesIO(base_image["image"]))

                    if is_image_a_scan_or_chart(pil_image):
                        logger.info(f"Inverting image {xref} (detected as chart/scan)")

                        if pil_image.mode == "RGBA":
                            r, g, b, a = pil_image.split()
                            rgb_image = Image.merge("RGB", (r, g, b))
                            inverted_rgb = ImageOps.invert(rgb_image)
                            pil_image = Image.merge("RGBA", (*inverted_rgb.split(), a))
                        else:
                            if pil_image.mode != "RGB":
                                pil_image = pil_image.convert("RGB")
                            pil_image = ImageOps.invert(pil_image)

                        buffer = io.BytesIO()
                        pil_image.save(buffer, format="PNG", optimize=True)
                        doc.update_image(xref, data=buffer.getvalue())

                except Exception as e:
                    logger.warning(f"Skipping image {xref} on page {page_num + 1}: {e}")

        except Exception as e:
            logger.warning(f"Error processing images on page {page_num + 1}: {e}")


@app.post("/convert")
async def convert_pdf(file: UploadFile = File(...)):
    """
    Endpoint to convert uploaded PDF to night mode.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    logger.info(f"Starting conversion for: {file.filename}")

    try:
        pdf_bytes = await file.read()
        logger.info(f"Read {len(pdf_bytes)} bytes from uploaded file")

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        logger.info(f"Opened PDF with {len(doc)} pages, {doc.xref_length()} objects")

        processed_xrefs = set()

        # Phase 1: Scan and process all Form XObjects
        logger.info("Phase 1: Scanning for Form XObjects...")
        form_xobjects_found = 0

        for xref in range(1, doc.xref_length()):
            try:
                subtype = doc.xref_get_key(xref, "Subtype")
                if subtype and subtype[1] == "/Form":
                    form_xobjects_found += 1
                    process_xobject_recursively(doc, xref, processed_xrefs)
            except:
                continue

        logger.info(f"Found and processed {form_xobjects_found} Form XObjects")

        # Phase 2: Process each page
        logger.info(f"Phase 2: Processing {len(doc)} pages...")

        for page_num, page in enumerate(doc.pages()):
            logger.info(f"  Processing page {page_num + 1}...")

            # 1. Clean contents
            try:
                page.clean_contents()
                logger.debug(f"    Cleaned page contents")
            except Exception as e:
                logger.debug(f"    Could not clean page contents: {e}")

            # 2. Process main content stream
            xref_list = page.get_contents()
            if xref_list:
                if not isinstance(xref_list, list):
                    xref_list = [xref_list]

                logger.debug(f"    Page has {len(xref_list)} content stream(s)")

                for xref in xref_list:
                    if xref in processed_xrefs:
                        continue

                    processed_xrefs.add(xref)

                    try:
                        stream = doc.xref_stream(xref)
                        if stream:
                            logger.debug(f"    Processing content stream {xref} ({len(stream)} bytes)")
                            new_stream = process_stream_content(stream, f"page {page_num + 1} stream {xref}")

                            if new_stream != stream:
                                doc.update_stream(xref, new_stream)
                                logger.debug(f"    Updated content stream {xref}")
                    except Exception as e:
                        logger.warning(f"    Error processing stream {xref}: {e}")
            else:
                logger.debug(f"    Page has no content streams")

            # 3. Draw dark background
            try:
                page.draw_rect(page.rect, color=None, fill=DARK_BG, overlay=False)
                logger.debug(f"    Added dark background")
            except Exception as e:
                logger.warning(f"    Could not draw background: {e}")

        # Phase 3: Process images
        logger.info("Phase 3: Processing images...")
        process_images_in_doc(doc)

        # Phase 4: Save
        logger.info("Phase 4: Saving converted PDF...")
        out_buffer = io.BytesIO()

        # Save with compression and cleanup
        save_options = {
            "garbage": 4,  # Remove unused objects
            "deflate": True,  # Compress
            "clean": True,  # Clean and repair
        }

        doc.save(out_buffer, **save_options)
        out_buffer.seek(0)

        output_size = out_buffer.getbuffer().nbytes
        logger.info(f"Saved PDF: {output_size} bytes")

        doc.close()

        # Create output filename
        filename = file.filename or "document.pdf"
        if filename.lower().endswith(".pdf"):
            output_name = f"night_{filename}"
        else:
            output_name = f"night_{filename}.pdf"

        logger.info(f"Conversion complete: {output_name}")

        return StreamingResponse(
            out_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={output_name}",
                "X-Conversion-Status": "success",
                "X-Original-Filename": filename,
                "X-Output-Size": str(output_size),
            },
        )

    except Exception as e:
        logger.error(f"Conversion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}") from e


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Platinum PDF Night Mode", "version": "2.0"}


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Platinum PDF Night Mode server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
