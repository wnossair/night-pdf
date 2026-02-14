# 🌙 Night PDF

> Transform PDFs into eye-friendly dark mode documents with intelligent color inversion

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/react-19.2-61dafb.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)](https://fastapi.tiangolo.com/)

Night PDF converts standard PDFs into dark mode-optimized documents perfect for nighttime reading. Using advanced color space analysis and intelligent inversion algorithms, it preserves readability while reducing eye strain.

## ✨ Features

- **🎨 Smart Color Inversion** - Preserves hue while intelligently adjusting brightness for optimal contrast
- **📊 Chart & Diagram Optimization** - Detects and inverts charts/scans while leaving photos untouched
- **🖼️ Image Intelligence** - Distinguishes between documents and photographs using brightness analysis
- **⚡ Fast Processing** - Handles multi-page documents efficiently with PyMuPDF
- **🌐 Modern Web UI** - Clean, responsive React interface with drag-and-drop support
- **📦 Zero Configuration** - Works out of the box with sensible defaults
- **🧪 Well Tested** - Comprehensive test suite with unit, integration, and API tests

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher (for frontend)
- pip and npm

### Installation

#### Backend Setup

```bash
cd backend
pip install -r requirements.txt
python main.py
```

The API will start on `http://localhost:8000`

#### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The UI will open at `http://localhost:5173`

### Docker Setup (Coming Soon)

```bash
docker-compose up
```

## 💻 Usage

### Web Interface

1. Open `http://localhost:5173` in your browser
2. Drag and drop your PDF or click to browse
3. Click "Convert to Night Mode"
4. Download your dark mode PDF

### API

```bash
curl -X POST "http://localhost:8000/convert" \
  -F "file=@document.pdf" \
  --output night_document.pdf
```

#### API Response Headers

- `X-Conversion-Status` - Conversion status (success/failed)
- `X-Original-Filename` - Original file name
- `X-Output-Size` - Output file size in bytes

### Python SDK (Programmatic Usage)

```python
import requests

with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/convert',
        files={'file': f}
    )

with open('night_document.pdf', 'wb') as f:
    f.write(response.content)
```

## 🏗️ Architecture

```
night-pdf/
├── backend/          # FastAPI Python backend
│   ├── main.py       # Core conversion logic
│   ├── tests/        # Test suite
│   └── requirements.txt
└── frontend/         # React + Vite frontend
    ├── src/
    │   ├── App.jsx   # Main UI component
    │   └── main.jsx
    └── package.json
```

### How It Works

1. **Color Space Analysis** - Converts RGB to HLS (Hue, Lightness, Saturation)
2. **Smart Inversion** - Applies context-aware inversion rules:
   - Very dark colors (L < 0.1) → Light gray for readability
   - Very light colors (L > 0.9) → Medium-dark gray
   - Colored text → Preserves hue, inverts lightness
3. **Image Detection** - Analyzes corner brightness and mean values to detect charts vs photos
4. **Stream Processing** - Parses and modifies PDF content streams to update colors
5. **Background Injection** - Adds dark background (#121212) to all pages

## 🧪 Development

### Setup Development Environment

```bash
# Backend
cd backend
pip install -r requirements-dev.txt

# Frontend
cd frontend
npm install
```

### Running Tests

```bash
# Backend tests
cd backend
pytest                          # Run all tests
pytest -v                       # Verbose output
pytest -m "not slow"           # Skip slow tests
pytest --cov                    # With coverage report

# Frontend tests
cd frontend
npm test
```

### Code Quality

```bash
# Backend linting and formatting
ruff check .                    # Lint
ruff format .                   # Format
mypy main.py                    # Type check

# Frontend linting
npm run lint
```

### Project Structure

- `invert_smart()` - Core color inversion algorithm using HLS color space
- `process_stream_content()` - Parses and modifies PDF content streams
- `is_image_a_scan_or_chart()` - Heuristic image classification
- `process_images_in_doc()` - Handles embedded images
- `process_xobject_recursively()` - Processes nested PDF objects

## 🔧 Configuration

### Backend Environment Variables

```bash
export LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
export MAX_FILE_SIZE=50        # Max upload size in MB
export CORS_ORIGINS="*"        # CORS allowed origins
```

### Customizing Color Inversion

Edit `DARK_BG` in [main.py](backend/main.py) to change the background color:

```python
DARK_BG = (18 / 255, 18 / 255, 18 / 255)  # #121212
```

## 🐛 Troubleshooting

### "Conversion failed" Error

- Ensure the file is a valid PDF
- Check file isn't password-protected or corrupted
- Verify file size is under system limits

### Colors Not Inverting Properly

- Some PDFs use images for text (scanned documents) - these may not invert perfectly
- Try adjusting the inversion thresholds in `invert_smart()`

### Backend Won't Start

```bash
# Check Python version
python --version  # Should be 3.8+

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Frontend Build Issues

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

## 📊 Performance

- **Small PDFs** (< 1MB): ~0.5-1 second
- **Medium PDFs** (1-10MB): ~2-5 seconds
- **Large PDFs** (10-50MB): ~5-15 seconds

_Performance varies based on PDF complexity, number of images, and system specifications._

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines

- Write tests for new features
- Follow existing code style (Ruff for Python, ESLint for JS)
- Update documentation for API changes
- Add type hints to Python functions

## 📝 API Documentation

### Endpoints

#### `POST /convert`

Convert a PDF to night mode.

**Request:**

- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: `file` (PDF file)

**Response:**

- Content-Type: `application/pdf`
- Headers: `X-Conversion-Status`, `X-Original-Filename`, `X-Output-Size`
- Body: Converted PDF binary

**Example:**

```bash
curl -X POST http://localhost:8000/convert \
  -F "file=@document.pdf" \
  -o night_document.pdf
```

#### `GET /health`

Health check endpoint.

**Response:**

```json
{
  "status": "healthy",
  "service": "Platinum PDF Night Mode",
  "version": "2.0"
}
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/) - PDF manipulation library
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://reactjs.org/) - UI framework
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS framework

## 📧 Contact

For questions or feedback, please open an issue on GitHub.

---

**Made with ❤️ for night owls and dark mode enthusiasts**
