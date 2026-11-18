"""Local adapters for the pinned Craft command-line engines."""
import csv
import json
import re
import shutil
import subprocess
from tempfile import TemporaryFile

import pdf_support
import word_document

from slides import edit_slides, preview_slides, append_slides

LIMIT = 64 * 1024 * 1024
BINARIES = {name: name + "craft-cli" for name in ("word", "grid", "deck", "pdf")}
FORMATS = {
    "word": {".txt", ".md", ".doc", ".docx", ".rtf", ".odt"},
    "sheet": {".csv", ".tsv", ".xls", ".xlsx", ".ods"},
    "slides": {".pptx", ".md"},
    "pdf": {".pdf"},
}


class RequestError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def available():
    return {name: shutil.which(binary) is not None for name, binary in BINARIES.items()}


def run(engine, *args, timeout=45):
    command = BINARIES.get(engine, engine)
    binary = shutil.which(command)
    if not binary:
        raise RequestError(f"Pasang {command} dan tambahkan ke PATH.", 503)
    with TemporaryFile() as output, TemporaryFile() as errors:
        try:
            process = subprocess.run([binary, *map(str, args)], stdout=output, stderr=errors,
                                     stdin=subprocess.DEVNULL, timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RequestError(f"{command} gagal dijalankan atau melebihi batas waktu.", 422) from exc
        if process.returncode:
            errors.seek(0)
            detail = errors.read(512).decode("utf-8", "replace").strip()
            raise RequestError(f"{command} menolak operasi. {detail}", 422)
        output.seek(0)
        data = output.read(LIMIT + 1)
        if len(data) > LIMIT:
            raise RequestError("Keluaran engine melewati 64 MiB.", 413)
        return data.decode("utf-8", "replace")


def file_result(output, mime="application/octet-stream"):
    if output.stat().st_size > LIMIT:
        raise RequestError("File hasil melewati 64 MiB.", 413)
    return output.read_bytes(), mime, output.name


def changes(fields):
    entries = json.loads(fields.get("changes", "[]"))
    if not isinstance(entries, list) or len(entries) > 1000 or not all(isinstance(entry, dict) for entry in entries):
        raise RequestError("Maksimal 1.000 perubahan objek per operasi.")
    return entries


def word(operation, source, output, fields):
    if operation == "replace":
        text = fields.get("text", "")
        if source.suffix in (".txt", ".md"):
            output.write_text(text, encoding="utf-8")
        elif source.suffix == ".docx":
            try:
                word_document.save_text(source, output, text)
            except word_document.EditError as exc:
                raise RequestError(str(exc), 422) from exc
        elif source.suffix in (".odt", ".rtf"):
            draft = source.with_name("draft.txt")
            draft.write_text(text, encoding="utf-8")
            run("word", "convert", draft, output)
        else:
            raise RequestError("Simpan ulang DOC sebagai DOCX di WordCraft terlebih dahulu.")
        return file_result(output)
    if operation in ("open", "extract"):
        if source.suffix == ".docx" and operation == "open":
            try:
                text = word_document.open_text(source)
            except word_document.EditError as exc:
                raise RequestError(str(exc), 422) from exc
        else:
            text = source.read_text(encoding="utf-8-sig") if source.suffix in (".txt", ".md") else run("word", "text", source)
        return {"text": text} if operation == "open" else (text.encode(), "text/plain; charset=utf-8", None)
    raise RequestError("Operasi Writer tidak tersedia.", 404)


def sheet_metadata(source):
    info = json.loads(run("grid", "info", source, "--json"))
    sheets = {entry["name"]: entry for entry in info["sheets"]}
    names = list(sheets)
    active = info.get("activeSheet", 0)
    return sheets, names[active if type(active) is int and 0 <= active < len(names) else 0]


def grid_preview(source, name):
    args = {"range": "A1:T50", "sheet": name}
    operations = [{"formatted": True}, {"formulas": True}, {}]
    commands = [arg for opts in operations for arg in ("--cmd", "sheet.read=" + json.dumps(args | opts))]
    response = run("grid", "run", "--in", source, *commands)
    values, inputs, calculated = [json.loads(line)["result"] for line in response.splitlines() if line.strip()]
    return values, inputs, calculated


def csv_rows(source):
    delimiter = "\t" if source.suffix == ".tsv" else ","
    with source.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.reader(file, delimiter=delimiter)), delimiter


def address_parts(address):
    match = re.fullmatch(r"([A-Z]{1,3})([1-9][0-9]{0,6})", address.upper())
    if not match:
        raise RequestError("Alamat sel tidak valid.")
    col = 0
    for letter in match[1]:
        col = col * 26 + ord(letter) - 64
    row = int(match[2])
    if col > 16384 or row > 1048576:
        raise RequestError("Alamat sel di luar batas workbook.")
    return row, col


def sheet(operation, source, output, fields):
    grid = available()["grid"]
    if not grid and (source.suffix not in (".csv", ".tsv") or operation in ("chart", "render")):
        raise RequestError("Pasang gridcraft-cli untuk membuka workbook Office.", 503)
    sheets, active = sheet_metadata(source) if grid else ({"Sheet1": {}}, "Sheet1")
    name = fields.get("sheet", active)
    if name not in sheets:
        raise RequestError("Worksheet tidak ditemukan.")
    if operation == "render":
        html = source.with_name("sheet.html")
        run("grid", "convert", source, html, "--sheet", name)
        return {"html": file_result(html)[0].decode("utf-8")}
    if operation == "chart":
        if source.suffix != ".xlsx":
            raise RequestError("Chart disimpan pada workbook XLSX.")
        cell_range, chart_type = fields.get("range", ""), fields.get("type", "")
        bounds = cell_range.split(":")
        if len(bounds) != 2 or chart_type not in {"column", "bar", "line", "pie", "doughnut", "area", "scatter"}:
            raise RequestError("Rentang atau jenis chart tidak valid.")
        start, end = map(address_parts, bounds)
        if end[0] < start[0] or end[1] < start[1] or (end[0]-start[0]+1)*(end[1]-start[1]+1) > 10000:
            raise RequestError("Gunakan rentang chart maju hingga 10.000 sel.")
        run("grid", "run", "--in", source, "--cmd", "sheet.activate=" + json.dumps({"sheet": name}),
            "--cmd", "insert.chart=" + json.dumps({"range": cell_range, "type": chart_type,
                                                   "title": fields.get("title", "")[:128]}),
            "--out", output, "--quiet")
        return file_result(output)
    entries = changes(fields) if operation in ("save", "preview-current") else []
    if operation == "cell":
        entries = [{"sheet": name, "address": fields.get("address", ""), "input": fields.get("value", "")}]
    rows, delimiter = csv_rows(source) if not grid else (None, None)
    current = source
    if entries:
        commands = []
        for entry in entries:
            address, value, tab = entry["address"], entry["input"], entry.get("sheet", name)
            row, col = address_parts(address)
            if tab not in sheets or not isinstance(value, str) or len(value) > 32767:
                raise RequestError("Worksheet atau input edit tidak valid.")
            if grid:
                commands.append({"command": "cell.set", "params": {"sheet": tab, "cell": address, "input": value}})
            else:
                if row > 10000 or col > 256:
                    raise RequestError("Edit CSV/TSV lokal melampaui 10.000 baris atau 256 kolom.")
                rows.extend([] for _ in range(len(rows), row))
                rows[row - 1].extend([""] * (col - len(rows[row - 1])))
                rows[row - 1][col - 1] = value
        if grid:
            intermediate = source.suffix not in (".xlsx", ".csv", ".tsv")
            if intermediate and operation != "preview-current":
                raise RequestError("Simpan workbook XLS/ODS sebagai XLSX di GridCraft sebelum mengedit.")
            script = source.with_name("sheet.jsonl")
            script.write_text("\n".join(map(json.dumps, commands)), encoding="utf-8")
            current = source.with_name("edited.xlsx")
            run("grid", "run", "--in", source, "--script", script, "--out", current, "--quiet")
        else:
            with output.open("w", encoding="utf-8", newline="") as file:
                csv.writer(file, delimiter=delimiter).writerows(rows)
            current = output
    if operation in ("save", "cell"):
        if current == source:
            shutil.copyfile(source, output)
        elif grid and output.suffix != current.suffix:
            run("grid", "convert", current, output, "--sheet", name)
        elif grid:
            current.replace(output)
        return file_result(output)
    if operation in ("open", "preview-current"):
        values, inputs, calculated = grid_preview(current, name) if grid else (rows, rows, [])
        width = max(1, min(20, max(map(len, inputs[:50]), default=0)))
        height = max(1, min(50, max(len(inputs), len(values))))
        def bounded(matrix):
            return [((matrix[i] if i < len(matrix) else []) + [""] * width)[:width] for i in range(height)]
        return {"workbook": {"sheet": name, "sheets": list(sheets), "startRow": 1, "startColumn": 1,
                             "range": f"A1:{chr(64 + width)}{height}", "values": bounded(values),
                             "inputs": bounded(inputs), "calculatedValues": bounded(calculated), "charts": sheets[name].get("charts", [])}}
    raise RequestError("Operasi spreadsheet belum tersedia.", 501)


def slides(operation, source, output, fields, outline=None):
    if operation == "open":
        return preview_slides(source)
    if operation == "save":
        edit_slides(source, output, changes(fields))
        return file_result(output)
    if operation == "roundtrip":
        run("deck", "convert", source, output)
        return file_result(output)
    if operation == "from-outline":
        if source.stat().st_size > 32768 or not source.read_text(encoding="utf-8").strip():
            raise RequestError("Outline wajib diisi, maksimal 32 KiB.")
        output = output.with_suffix(".pptx")
        run("deck", "convert", source, output)
        return file_result(output)
    if operation == "append-outline":
        if not outline or not outline.strip() or len(outline.encode()) > 32768:
            raise RequestError("Outline wajib diisi, maksimal 32 KiB.")
        draft = source.with_name("outline.md")
        draft.write_text(outline, encoding="utf-8")
        generated = source.with_name("generated.pptx")
        run("deck", "convert", draft, generated)
        append_slides(source, generated, output, changes(fields))
        return file_result(output)
    if re.fullmatch(r"render/[1-9][0-9]{0,3}", operation):
        image = output.with_suffix(".png")
        index = int(operation.split("/")[-1]) - 1
        run("deck", "render", source, "--slide", index, "--scale", "1", image)
        return file_result(image, "image/png")
    raise RequestError("Operasi Slides belum tersedia.", 501)


def ocr_languages():
    if not shutil.which("ocrmypdf") or not shutil.which("tesseract"):
        return []
    try:
        languages = set(run("tesseract", "--list-langs", timeout=4).splitlines())
    except RequestError:
        return []
    supported = [name for name in ("eng", "ind") if name in languages]
    if len(supported) == 2:
        supported.append("ind+eng")
    return supported


def pdf(operation, source, output, fields):
    page = re.fullmatch(r"page/([1-9][0-9]{0,5})", operation)
    kind = "page" if page else operation
    craft = bool(shutil.which(BINARIES["pdf"]))
    if kind in ("pages", "note") and not pdf_support.available():
        raise RequestError("Pasang dependensi PDF opsional untuk menyunting salinan PDF.", 503)
    result = pdf_support.handle(source, output, kind, fields | ({"page": page[1]} if page else {}),
                                prefer_craft=craft)
    if result is True:
        return file_result(output, "application/pdf")
    if kind == "ocr":
        language = fields.get("language", "eng")
        if language not in ocr_languages():
            raise RequestError("Model OCR untuk bahasa ini belum terpasang.", 503)
        if craft:
            info = json.loads(run("pdf", "info", source))
            if info.get("encrypted"):
                raise RequestError("OCR PDF terenkripsi belum tersedia.", 422)
            pages = int(info["pages"])
        else:
            if not result:
                raise RequestError("Gunakan PDF tanpa enkripsi dan pasang dependensi PDF opsional.", 503)
            pages = result["pageCount"]
        if pages > 30:
            raise RequestError("OCR dibatasi hingga 30 halaman.", 413)
        run("ocrmypdf", "--language", language, "--skip-text", "--output-type", "pdf", "--optimize", 0,
            "--jobs", 1, source, output, timeout=120)
        return file_result(output, "application/pdf")
    if result is not None:
        return result
    if not craft:
        raise RequestError("Pasang pdfcraft-cli atau dependensi PDF opsional untuk membuka PDF.", 503)
    info = json.loads(run("pdf", "info", source))
    if info.get("encrypted"):
        raise RequestError("Pasang dependensi PDF opsional untuk membuka PDF terenkripsi.", 503)
    if kind == "open-save":
        run("pdf", "edit", source, "--out", output)
        return file_result(output, "application/pdf")
    if kind == "open":
        return pdf_support.preview(int(info["pages"]), lambda n: run("pdf", "text", source, "--page", n))
    if page:
        image = output.with_suffix(".png")
        run("pdf", "render", source, "--page", page[1], "--dpi", "96", "--out", image)
        return file_result(image, "image/png")
    raise RequestError("Operasi PDF belum tersedia.", 501)
