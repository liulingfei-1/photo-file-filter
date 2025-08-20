# Photo File Filter

[中文说明](README.md)

Photo File Filter is a lightweight yet reliable tool for filtering photos and batch renaming. It supports matching filenames based on a reference table or using an AI multimodal model to generate descriptive names.

## Features
- Locate required photos by a reference table and copy them to the target directory with new names.
- Preserve original extensions and binary data.
- Fuzzy matching to reduce missed files.
- Optional AI naming via Tongyi Qianwen multimodal model.
- Supports JPG/PNG/GIF/TIFF/WebP/BMP and RAW formats such as CR2/NEF/ARW/DNG/ORF/RW2/PEF/SRW/RAF/X3F.
- Double-check copied files with file size and SHA‑256; failed copies retry automatically.

## Installation
Requires Python 3.9+.

```bash
pip install -r requirements.txt
# Optional HEIC/HEIF support
pip install pillow-heif
```

## Reference Table Format
- **Classic mode** (two columns): 1) identifier 2) note (final filename). See `example_reference.csv`.
- **AI naming mode** (one column): 1) identifier used to match filenames. See `example_reference_ai.csv`.

## Command Line Usage
```bash
# Classic mode: match & rename according to the reference table
python file_filter.py \
  --source /path/to/photos \
  --target /path/to/output \
  --reference example_reference.csv

# AI naming mode: AI generates filenames, original data and extensions are kept
python file_filter.py \
  --source /path/to/photos \
  --target /path/to/output \
  --reference example_reference_ai.csv \
  --ai-naming
```

Arguments:
- `--source/-s`: source directory
- `--target/-t`: output directory (auto created)
- `--reference/-r`: reference table (CSV/Excel)
- `--ai-naming`: enable AI-based naming

## Graphical Interface
On macOS or Windows:

```bash
python gui_app.py
```

Choose source, target and reference table in the GUI; optionally enable "Use AI naming" and click "Start" to process.

## AI Naming Workflow
- AI is used only to generate descriptive filenames; original files remain untouched.
- Images are temporarily resized to JPG (≤1024×768) for analysis and deleted afterward.
- Uses the Tongyi Qianwen multimodal endpoint:
  - Endpoint: `https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation`
  - Payload `input.messages[].content` includes both `{ "image": "data:image/jpeg;base64,..." }` and `{ "text": "..." }`
- Set your API key in `file_filter.py` (`QWEN_API_KEY`).
- Recommended dependencies: `rawpy` for RAW decoding and `pillow-heif` for HEIC/HEIF.

### Default Thresholds (editable at top of `file_filter.py`)
- `AI_REQUEST_TIMEOUT_S = 40`: request timeout in seconds
- `AI_REQUEST_MAX_RETRIES = 2`: retries on 429/5xx/timeout (exponential backoff)
- `AI_REQUEST_QPS = 1.0`: global rate limit (requests per second)
- Pre-upload resize: max 1024×768
- Files larger than 50MB skip AI analysis
- Filename cleaning: remove illegal characters and trailing extensions; replace whitespace with underscores

Known limitations:
- Images with the shortest side ≤10px are rejected (HTTP 400).
- Some RAW files may fail to decode and will be skipped.

## Supported Formats
- Common: JPG/JPEG, PNG, GIF, TIFF/TIF, WebP, BMP, HEIC/HEIF
- RAW: CR2, NEF, ARW, DNG, ORF, RW2, PEF, SRW, RAF, X3F

## Examples

```bash
# Classic mode
python file_filter.py \
  --source ./photos \
  --target ./output \
  --reference ./example_reference.csv

# AI naming mode
python file_filter.py \
  --source ./photos \
  --target ./output \
  --reference ./example_reference_ai.csv \
  --ai-naming
```

## Packaging
A `PhotoFilterGUI.spec` is provided for one-command GUI packaging:

```bash
python -m PyInstaller --noconfirm PhotoFilterGUI.spec
# Output located in dist/PhotoFilterGUI or PhotoFilterGUI.app (macOS)
```

Push a tag to trigger GitHub Actions build and release (macOS/Windows):

```bash
git tag v1.1.0
git push origin v1.1.0
```

## Testing

```bash
pip install -r requirements.txt
pytest
```

## FAQ
- **HTTP 400 from AI**: the image is usually too small (e.g., 8×12). Enlarge the shortest side and retry.
- **Cannot read HEIC**: install `pillow-heif` and try again.
- **Slow RAW processing**: lower the max size or increase QPS in the source code (consider API quota).
