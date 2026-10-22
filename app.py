"""DocShift Streamlit application."""

from __future__ import annotations

import logging
from pathlib import Path

import streamlit as st

from src.config import CONFIG
from src.converter import convert_pdf_to_docx
from src.exceptions import DocShiftError
from src.file_manager import TempWorkspace, format_bytes
from src.ocr import get_ocr_status
from src.pdf_inspector import extract_embedded_images, inspect_pdf
from src.validators import validate_pdf_bytes

ROOT = Path(__file__).resolve().parent
STYLES = ROOT / "assets" / "styles.css"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("docshift")


def load_css() -> None:
    if STYLES.exists():
        st.markdown(f"<style>{STYLES.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def init_state() -> None:
    defaults = {
        "workspace": None,
        "pdf_path": None,
        "inspection": None,
        "result": None,
        "docx_bytes": None,
        "images_zip": None,
        "error": None,
        "status": None,
        "source_name": None,
        "converted": False,
        "upload_token": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_workspace() -> None:
    workspace = st.session_state.get("workspace")
    if workspace is not None:
        try:
            workspace.cleanup()
        except Exception:
            logger.warning("Session workspace cleanup failed.")
    for key in (
        "workspace",
        "pdf_path",
        "inspection",
        "result",
        "docx_bytes",
        "images_zip",
        "error",
        "status",
        "source_name",
        "upload_token",
    ):
        st.session_state[key] = None
    st.session_state.converted = False


def render_header() -> None:
    st.markdown(
        """
        <div class="ds-brand">
          <div class="ds-mark">DS</div>
          <div>
            <div class="ds-brand-name">DocShift</div>
            <div class="ds-kicker">Professional PDF to Word converter</div>
          </div>
        </div>
        <div class="ds-hero">
          <h1>Convert PDF to Word</h1>
          <p class="ds-subtitle">Turn your PDFs into editable Word documents.</p>
          <p class="ds-support">Preserve text, tables, images, and layout as accurately as possible.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_meta(filename: str, size: int, pages: int) -> None:
    safe_name = (
        filename.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    st.markdown(
        f"""
        <div class="ds-meta">
          <div class="ds-meta-item"><div class="ds-meta-label">File</div><div class="ds-meta-value">{safe_name}</div></div>
          <div class="ds-meta-item"><div class="ds-meta-label">Size</div><div class="ds-meta-value">{format_bytes(size)}</div></div>
          <div class="ds-meta-item"><div class="ds-meta-label">Pages</div><div class="ds-meta-value">{pages}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def prepare_upload(uploaded) -> None:
    token = f"{uploaded.name}:{uploaded.size}"
    if st.session_state.upload_token == token and st.session_state.inspection is not None:
        return
    reset_workspace()
    data = uploaded.getvalue()
    validate_pdf_bytes(data, uploaded.name)
    workspace = TempWorkspace()
    pdf_path = workspace.save_upload(data, uploaded.name)
    inspection = inspect_pdf(pdf_path)
    st.session_state.workspace = workspace
    st.session_state.pdf_path = str(pdf_path)
    st.session_state.inspection = inspection
    st.session_state.source_name = Path(uploaded.name).name
    st.session_state.upload_token = token
    st.session_state.error = None


def main() -> None:
    st.set_page_config(page_title="DocShift — Convert PDF to Word", page_icon="📄", layout="centered")
    load_css()
    init_state()
    render_header()

    ocr_status = get_ocr_status()

    uploaded = st.file_uploader(
        "Drag and drop a PDF, or browse",
        type=["pdf"],
        help=f"Maximum size {CONFIG.max_upload_mb} MB and {CONFIG.max_pages} pages by default.",
    )

    if uploaded is None and st.session_state.upload_token is not None:
        reset_workspace()

    if uploaded is not None:
        try:
            prepare_upload(uploaded)
        except DocShiftError as exc:
            logger.warning("Upload rejected: %s", exc.log_message)
            st.session_state.error = exc.user_message
        except Exception:
            logger.exception("Unexpected upload failure.")
            st.session_state.error = "The PDF could not be read. Try another file."

    col_a, col_b = st.columns(2)
    with col_a:
        use_ocr = st.checkbox(
            "Use OCR for scanned PDFs",
            value=False,
            disabled=not ocr_status.available,
            help="Runs local Tesseract. Optional for ordinary text PDFs and may add recognition errors.",
        )
    with col_b:
        extract_images = st.checkbox(
            "Also extract images as a ZIP",
            value=False,
            help="Saves pictures embedded in the PDF so you can reuse them separately.",
        )

    if ocr_status.available:
        st.caption(ocr_status.message)
    else:
        st.caption(
            ocr_status.message
            + " On Windows, install Tesseract OCR (UB Mannheim build) and keep the English language data."
        )

    convert_clicked = st.button("Convert to Word", type="primary", use_container_width=True)

    if convert_clicked:
        if uploaded is None or not st.session_state.pdf_path:
            st.session_state.error = "Choose a PDF first, then select Convert to Word."
        else:
            try:
                status_box = st.empty()

                def on_progress(message: str) -> None:
                    st.session_state.status = message
                    status_box.markdown(
                        f'<div class="ds-status info">{message}</div>',
                        unsafe_allow_html=True,
                    )

                pdf_path = Path(st.session_state.pdf_path)
                inspection = st.session_state.inspection
                workspace = st.session_state.workspace
                should_ocr = bool(use_ocr and ocr_status.available)
                if use_ocr and not ocr_status.available:
                    raise DocShiftError(ocr_status.message)
                docx_path = workspace.output_path(uploaded.name)
                result = convert_pdf_to_docx(
                    pdf_path,
                    docx_path,
                    original_name=uploaded.name,
                    use_ocr=should_ocr,
                    inspection=inspection,
                    progress=on_progress,
                )
                st.session_state.docx_bytes = docx_path.read_bytes()
                if extract_images:
                    on_progress("Extracting images…")
                    zip_path = workspace.images_zip_path()
                    count = extract_embedded_images(pdf_path, zip_path)
                    result.images_extracted = count
                    if count == 0:
                        result.warnings.append("No extractable embedded images were found in this PDF.")
                    else:
                        st.session_state.images_zip = zip_path.read_bytes()
                st.session_state.result = result
                st.session_state.converted = True
                st.session_state.error = None
                workspace.cleanup()
                st.session_state.workspace = None
                st.session_state.pdf_path = None
            except DocShiftError as exc:
                logger.warning("Conversion blocked: %s", exc.log_message)
                st.session_state.error = exc.user_message
                st.session_state.converted = False
            except Exception:
                logger.exception("Unexpected conversion failure.")
                st.session_state.error = "Something went wrong during conversion. Try another PDF or a smaller file."
                st.session_state.converted = False

    if st.session_state.error:
        st.markdown(
            f'<div class="ds-status err">{st.session_state.error}</div>',
            unsafe_allow_html=True,
        )

    inspection = st.session_state.inspection
    if uploaded is not None and inspection is not None:
        st.subheader("Document details")
        render_meta(
            st.session_state.source_name or uploaded.name,
            inspection.file_size,
            inspection.page_count,
        )
        extras = []
        if inspection.image_count:
            extras.append(f"{inspection.image_count} embedded image(s) detected")
        if inspection.has_tables_hint:
            extras.append("table-like structures detected")
        if extras:
            st.caption(" · ".join(extras))
        if inspection.likely_scanned:
            st.markdown(
                '<div class="ds-status warn">This PDF appears scanned or image-based. '
                "Enable OCR if Tesseract is installed.</div>",
                unsafe_allow_html=True,
            )

    result = st.session_state.result
    if st.session_state.converted and result and st.session_state.docx_bytes:
        st.subheader("Ready to download")
        st.markdown(
            '<div class="ds-status ok">Conversion succeeded. This is a real Word (.docx) file.</div>',
            unsafe_allow_html=True,
        )
        render_meta(result.output_name, result.output_size, result.page_count)
        st.write(
            f"Source: **{result.source_name}** ({result.source_size_label}) → "
            f"**{result.output_name}** ({result.output_size_label})"
        )
        if result.used_ocr:
            st.info("OCR text was used. Expect possible spelling and layout mistakes.")
        unique_warnings = list(dict.fromkeys(result.warnings))
        if unique_warnings:
            st.markdown("**Please note**")
            for warning in unique_warnings:
                st.markdown(f"- {warning}")
        st.download_button(
            "Download Word document",
            data=st.session_state.docx_bytes,
            file_name=result.output_name,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
        if st.session_state.images_zip:
            st.download_button(
                "Download extracted images",
                data=st.session_state.images_zip,
                file_name=f"{Path(result.output_name).stem}-images.zip",
                mime="application/zip",
                use_container_width=True,
            )
        if st.button("Convert another file", use_container_width=True):
            reset_workspace()
            st.rerun()

    st.markdown(
        f"""
        <div class="ds-footer">
          <strong>Privacy.</strong> Files are processed on this computer or host for your current session only.
          Uploads are written to a unique temporary folder, converted, then deleted. DocShift does not send your
          PDF to a paid API and does not store document text in logs. Limits: {CONFIG.max_upload_mb} MB and
          {CONFIG.max_pages} pages unless you change the environment settings. Actual capacity also depends on RAM,
          disk space, and hosting timeouts. This tool is not a substitute for a security or compliance audit.
          <br><br>
          DocShift · Local PDF to Word conversion · Layout quality varies with the original PDF
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
