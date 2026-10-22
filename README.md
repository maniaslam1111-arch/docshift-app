# DocShift — Convert PDF to Word

DocShift is a local web app that turns a PDF into a real editable Word (`.docx`) file. It runs on your computer with Python and Streamlit. It does not require a paid API.

Conversion quality depends on the original PDF. Simple text, tables, and images usually convert well. Complex magazines, forms, and vector artwork often need manual cleanup in Word.

## What you need

- Windows 10 or later
- Python 3.10, 3.11, or 3.12 is recommended (Python 3.13+ may work if packages provide wheels)
- About 300 MB of disk space for Python packages
- Optional: [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) for scanned PDFs

## Windows setup (beginner)

Open **PowerShell**. Go to this project folder:

```powershell
cd "E:\coding project\pdf to word"
```

Create a virtual environment (an isolated Python folder for this project):

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If Windows blocks the script, run this once in PowerShell, then try activation again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Install the libraries:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Start the app:

```powershell
python -m streamlit run app.py
```

Your browser should open a local page (usually `http://localhost:8501`). Keep the PowerShell window open while you use DocShift.

## How to convert a file

1. Drag a PDF onto the upload box, or use the file picker.
2. Check the filename, size, and page count.
3. If the app says the PDF looks scanned, you may turn on OCR (only if Tesseract is installed).
4. Optionally extract images into a ZIP.
5. Select **Convert to Word**.
6. Download the `.docx` file and open it in Microsoft Word or a compatible editor.
7. Select **Convert another file** to start over.

DocShift never renames a PDF and pretends it is Word. The download is a real Office Open XML document.

## Optional OCR (scanned PDFs)

Ordinary text PDFs do **not** need OCR.

For scans:

1. Install Tesseract for Windows (UB Mannheim installer is the usual choice).
2. During setup, keep English language data (`eng`). Add other languages if you need them.
3. Confirm `tesseract` is on your PATH, or accept the default install folder `C:\Program Files\Tesseract-OCR\`.
4. Restart the terminal, start DocShift again, and enable **Use OCR for scanned PDFs**.

OCR can misread letters and will not perfectly rebuild the original layout. Review the Word file.

## Limits for larger PDFs

Default limits (change them in `.env` using `.env.example` as a guide):

- Upload size: 50 MB
- Page count: 200 pages
- Streamlit also has its own upload cap (see `.streamlit/config.toml`)

These are not unlimited. A 200-page file full of images can still fail if the computer runs out of RAM or disk space. Hosting platforms add their own timeouts and memory caps.

DocShift converts the document as a whole when using `pdf2docx`, because splitting pages can break layout.

## Project layout

- `app.py` — website and conversion workflow
- `src/converter.py` — PDF to Word engine
- `src/pdf_inspector.py` — page count, encryption, scan detection
- `src/file_manager.py` — temporary files
- `src/validators.py` — safe names and DOCX checks
- `src/ocr.py` — optional Tesseract
- `tests/` — automated tests
- `assets/styles.css` — visual style

## Tests

With the virtual environment active:

```powershell
python -m pytest -q
```

## Troubleshooting

| Problem | What to try |
| --- | --- |
| `Activate.ps1` is blocked | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `streamlit` is not recognized | Activate `.venv`, then `python -m pip install -r requirements.txt` |
| Password-protected PDF | Remove the password, then upload again |
| Scanned PDF has no text | Install Tesseract and enable OCR |
| Conversion fails on a design-heavy PDF | Try exporting a simpler PDF, or expect manual Word edits |
| File too large | Split the PDF, or raise `DOCSHIFT_MAX_UPLOAD_MB` and Streamlit `maxUploadSize` if the machine can handle it |
| Package install fails on a very new Python | Use Python 3.12 and a fresh `.venv` |

## Deployment (optional)

The app can run on any host that supports Python and Streamlit, including Streamlit Community Cloud.

Required files:

- `app.py`
- `requirements.txt`
- `runtime.txt` (Python 3.12 on Streamlit Cloud)
- `packages.txt` (installs Tesseract on Debian-based hosts; optional)

Before you put this on a public server:

- Set conservative upload, memory, and timeout limits.
- Understand that users will upload private files to **your** server.
- Temporary files are deleted after conversion in this app, but a public host is still not a certified compliance product.
- OCR needs the Tesseract system package; many free hosts have short CPU time limits.

Do not claim the live site is deployed until you have actually published it and opened it in a browser.

## Honest limitations

- Headings, lists, headers, and footers are preserved only when the conversion library can detect them.
- Charts and diagrams are usually kept as pictures, not as editable Word drawing objects.
- Merged or nested tables may flatten or shift.
- Annotations, form fields, and some vector graphics may be dropped or rasterized.
- Page count of the Word file is not independently guaranteed by Office XML; DocShift reports the source PDF page count.
