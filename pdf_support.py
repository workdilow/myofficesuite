"""Optional in-process PDFium operations for local viewing and page copies."""
from contextlib import closing
from ctypes import c_ushort
import io
import math
import re
from threading import Lock

try:
    import pypdfium2 as pdfium
    from pypdfium2 import raw
    from PIL import Image  # Required by PdfBitmap.to_pil().
except (ImportError, OSError):
    pdfium = raw = Image = None

LOCK = Lock()
COPY_PERMISSION = 1 << 4
MAX_RENDER_SIDE = 2400
MAX_PAGE_SELECTION = 250


class PdfError(Exception):
    def __init__(self, text, status=422):
        super().__init__(text)
        self.status = status


def available():
    return pdfium is not None


def preview(count, read_page, *, encrypted=False, allow_text=True):
    pages = []
    remaining = 100000
    truncated = False
    if allow_text:
        for number in range(1, min(count, 12) + 1):
            if remaining == 0:
                break
            text = read_page(number).strip()
            truncated = len(text) > remaining
            pages.append(text[:remaining])
            remaining -= len(pages[-1])
    text = "\n\n".join(f"--- Halaman {index} ---\n{page}" for index, page in enumerate(pages, 1))
    return {"text": text, "pageTexts": pages, "pageCount": count, "pagesExtracted": len(pages),
            "encrypted": encrypted, "copyRestricted": not allow_text,
            "textLimitReached": allow_text and (len(pages) < count or truncated)}


def handle(source, output, operation, fields, *, prefer_craft):
    if not available():
        return None
    password = fields.get("password", "")
    if "\x00" in password or len(password.encode()) > 1024:
        raise PdfError("Password PDF tidak valid.", 400)
    try:
        with LOCK:
            try:
                document = pdfium.PdfDocument(source, password=password or None)
            except pdfium.PdfiumError as exc:
                if exc.err_code == raw.FPDF_ERR_PASSWORD:
                    status = 401 if operation == "open" or operation == "page" else 422
                    raise PdfError("PDF ini memerlukan password yang benar.", status) from exc
                if prefer_craft and operation in ("open", "open-save", "page"):
                    return None
                raise
            with document:
                return process(document, output, operation, fields, prefer_craft)
    except (pdfium.PdfiumError, OverflowError) as exc:
        raise PdfError("PDF tidak dapat dibaca atau diproses oleh PDFium.") from exc


def process(document, output, operation, fields, prefer_craft):
    encrypted = raw.FPDF_GetSecurityHandlerRevision(document) >= 0
    if encrypted and operation not in ("open", "page"):
        raise PdfError("PDF terenkripsi hanya bisa ditampilkan dan dibaca sesuai izin dokumennya.")
    if not encrypted and prefer_craft and operation not in ("pages", "note"):
        return None
    count = len(document)
    if count == 0:
        raise PdfError("PDF tidak memiliki halaman.")
    allowed = not encrypted or bool(raw.FPDF_GetDocPermissions(document) & COPY_PERMISSION)
    if operation == "ocr":
        return {"pageCount": count}
    if operation == "open":
        def read(number):
            with closing(document[number - 1]) as page, closing(page.get_textpage()) as textpage:
                return textpage.get_text_bounded()
        return preview(count, read, encrypted=encrypted, allow_text=allowed)
    if operation == "page":
        number = int(fields["page"])
        if not 1 <= number <= count:
            raise PdfError("Nomor halaman di luar dokumen.", 400)
        with closing(document[number - 1]) as page:
            width, height = page.get_size()
            if not all(math.isfinite(size) and size > 0 for size in (width, height)):
                raise PdfError("Ukuran halaman PDF tidak valid.")
            scale = min(96 / 72, MAX_RENDER_SIDE / max(width, height))
            with closing(page.render(scale=scale, may_draw_forms=False, draw_annots=True)) as bitmap:
                image = io.BytesIO()
                bitmap.to_pil().save(image, format="PNG")
                return image.getvalue(), "image/png", None
    if operation == "pages":
        edit_pages(document, count, output, fields)
        return True
    if operation == "note":
        add_note(document, count, output, fields)
        return True
    return None


def add_note(document, count, output, fields):
    number = fields.get("page", "")
    text = fields.get("text", "").strip()
    if not re.fullmatch(r"[1-9][0-9]{0,5}", number) or int(number) > count:
        raise PdfError("Nomor halaman catatan tidak valid.", 400)
    if not text or len(text) > 2000 or "\x00" in text:
        raise PdfError("Isi catatan harus 1–2.000 karakter.", 400)
    with closing(document[int(number) - 1]) as page:
        left, bottom, right, top = page.get_bbox()
        size = min(20, (top - bottom) / 2, (right - left) / 2)
        if not math.isfinite(size) or size <= 0:
            raise PdfError("Ukuran halaman PDF tidak valid.")
        annot = raw.FPDFPage_CreateAnnot(page, raw.FPDF_ANNOT_TEXT)
        if not annot:
            raise PdfError("Catatan PDF tidak dapat ditambahkan.")
        try:
            rect = raw.FS_RECTF(left + size, top - size, left + 2 * size, top - 2 * size)
            payload = (text + "\x00").encode("utf-16-le")
            content = (c_ushort * (len(payload) // 2)).from_buffer_copy(payload)
            if not raw.FPDFAnnot_SetRect(annot, rect) or not raw.FPDFAnnot_SetStringValue(annot, b"Contents", content):
                raise PdfError("Catatan PDF tidak dapat disimpan.")
        finally:
            raw.FPDFPage_CloseAnnot(annot)
    document.save(output)


def selected_pages(expression, count):
    if not expression or len(expression) > 2048:
        raise PdfError("Masukkan urutan halaman seperti 3,1-2.", 400)
    selected = []
    for token in expression.split(","):
        match = re.fullmatch(r"\s*([1-9][0-9]{0,5})(?:\s*-\s*([1-9][0-9]{0,5}))?\s*", token)
        if not match:
            raise PdfError("Gunakan daftar halaman seperti 3,1-2.", 400)
        first = int(match[1])
        last = int(match[2] or first)
        if not 1 <= first <= last <= count or len(selected) + last - first + 1 > MAX_PAGE_SELECTION:
            raise PdfError(f"Periksa nomor halaman. Maksimal {MAX_PAGE_SELECTION} halaman per salinan.", 400)
        selected.extend(range(first - 1, last))
    if len(set(selected)) != len(selected):
        raise PdfError("Nomor halaman tidak boleh berulang.", 400)
    return selected


def edit_pages(document, count, output, fields):
    selected = selected_pages(fields.get("selection", ""), count)
    degrees = fields.get("rotation", "0")
    if degrees not in {"0", "90", "180", "270"}:
        raise PdfError("Rotasi harus 0, 90, 180, atau 270 derajat.", 400)
    with pdfium.PdfDocument.new() as copy:
        copy.import_pages(document, pages=selected)
        if degrees != "0":
            for index in range(len(copy)):
                with closing(copy[index]) as page:
                    page.set_rotation((page.get_rotation() + int(degrees)) % 360)
        copy.save(output)
