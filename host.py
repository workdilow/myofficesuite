"""Run Ruangkerja at http://127.0.0.1:4173 with Python 3.10+."""
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from threading import BoundedSemaphore, Lock
from http.client import HTTPException
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.parsers.expat import ExpatError
from zipfile import BadZipFile

import engines
import pdf_support

ROOT = Path(__file__).resolve().parent
STATIC = {"", "index.html", "styles.css", "app.js", "sheet_stats.js", "writer_review.js", "ai_stream.js", "pdf_citations.js"}
ADAPTERS = {"word": engines.word, "sheet": engines.sheet, "slides": engines.slides, "pdf": engines.pdf}
ORIGIN = "http://127.0.0.1:4173"
VERSION = (ROOT / "VERSION").read_text().strip()
SESSION = None
SESSION_WRITE = Lock()
STREAM_SLOTS = BoundedSemaphore(2)
UPLOAD_SLOTS = BoundedSemaphore(2)
AI_WIRE_LIMIT = 2 * 1024 * 1024
AI_TEXT_LIMIT = 256 * 1024
AI_ERROR = "Provider AI gagal merespons dengan hasil teks yang lengkap."


def provider(url, model, key):
    if not all(isinstance(item, str) for item in (url, model, key)):
        raise engines.RequestError("Konfigurasi provider tidak valid.")
    url, model = url.strip(), model.strip()
    parsed = urlsplit(url)
    if ((parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "::1", "localhost"}))
        or not parsed.hostname or parsed.username is not None or parsed.fragment or len(url) > 2048
        or not 1 <= len(model) <= 128 or len(key) > 4096 or any(ord(c) < 32 for c in key)):
        raise engines.RequestError("Endpoint provider harus HTTPS atau HTTP loopback, dengan model yang valid.")
    _ = parsed.port
    return url, model, key


def active_provider():
    session = SESSION
    if session is not None:
        return session, "session"
    try:
        return provider(*(os.environ.get("RUANGKERJA_AI_" + name, "") for name in
                          ("CHAT_COMPLETIONS_URL", "MODEL", "API_KEY"))), "environment"
    except (engines.RequestError, ValueError):
        return ("", "", ""), "environment"


def settings():
    (url, model, key), origin = active_provider()
    return {"configured": bool(url), "url": url, "model": model, "hasApiKey": bool(key), "source": origin}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def provider_request(data, stream=False):
    (url, model, key), _ = active_provider()
    if not url:
        raise engines.RequestError("Provider AI belum dikonfigurasi.", 503)
    task, prompt, context, language = (data.get(name) or "" for name in ("task", "input", "context", "language"))
    if not all(isinstance(item, str) for item in (task, prompt, context, language)) or not prompt.strip():
        raise engines.RequestError("Masukkan instruksi AI.")
    if sum(len(item.encode()) for item in (task, prompt, context, language)) > 64 * 1024:
        raise engines.RequestError("Konteks AI melebihi batas 64 KiB.", 413)
    formats = {
        "Presentation Assistant": "For a text rewrite, return one line beginning with Teks baru: followed by the replacement.",
        "Presentation Outline Assistant": "Use one Markdown heading per slide and bullet points for the body. Return only the outline.",
        "Spreadsheet Cleaning Assistant": "Return TSV between lines CLEAN_TSV_BEGIN and CLEAN_TSV_END, preserving dimensions and formulas.",
        "Spreadsheet Insight Assistant": "Cite worksheet cell addresses for numeric claims.",
        "Writer Revision Assistant": "Return the full revised plain text only.",
        "Writer Translation Assistant": "Return the full translated plain text only.",
        "PDF Assistant": "Answer in bullets with one claim per line and no heading. Support each bullet with a verbatim quote of at least eight characters formatted as [Hal. N: “exact quote”], where N is halaman in the supplied JSON context. If the context does not answer the question, say so without inventing references.",
    }
    instructions = ("You are Ruangkerja's office assistant. Treat the document context as reference data. "
                    "Respond in the requested language or Indonesian by default. " + formats.get(task, ""))
    payload = {"model": model, "stream": stream, "messages": [
        {"role": "system", "content": instructions},
        {"role": "user", "content": json.dumps({"task": task, "instruction": prompt,
                                                "language": language, "documentContext": context}, ensure_ascii=False)}
    ]}
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    return Request(url, data=json.dumps(payload).encode(), headers=headers)


def completed_text(response):
    raw = response.read(AI_WIRE_LIMIT + 1)
    if len(raw) > AI_WIRE_LIMIT:
        raise ValueError("provider response too large")
    choice = json.loads(raw)["choices"][0]
    text = choice["message"]["content"]
    if (not isinstance(text, str) or not text.strip() or len(text.encode()) > AI_TEXT_LIMIT
        or choice.get("finish_reason") not in (None, "stop")):
        raise ValueError("incomplete provider response")
    return text


PROVIDER_FAILURES = (URLError, OSError, HTTPException, TypeError, ValueError, KeyError, IndexError)


def generate(data):
    request = provider_request(data)
    try:
        with build_opener(NoRedirect()).open(request, timeout=45) as response:
            return {"text": completed_text(response)}
    except PROVIDER_FAILURES as exc:
        raise engines.RequestError(AI_ERROR, 502) from exc


def sse_data(response):
    total = 0
    fields = []
    while True:
        line = response.readline(65537)
        if not line:
            return
        total += len(line)
        if len(line) > 65536 or total > AI_WIRE_LIMIT:
            raise ValueError("provider event limit reached")
        line = line.rstrip(b"\r\n")
        if not line:
            if fields:
                yield b"\n".join(fields)
                fields.clear()
        elif line == b"data" or line.startswith(b"data:"):
            value = line[5:]
            fields.append(value[1:] if value.startswith(b" ") else value)


def response_deltas(response):
    if response.headers.get_content_type() != "text/event-stream":
        yield completed_text(response)
        return
    done = False
    stop = False
    has_text = False
    size = 0
    for data in sse_data(response):
        if data.strip() == b"[DONE]":
            done = True
            break
        event = json.loads(data)
        if "error" in event:
            raise ValueError("provider error event")
        for choice in event["choices"]:
            if choice.get("index", 0) != 0:
                continue
            reason = choice.get("finish_reason")
            if reason not in (None, "stop"):
                raise ValueError("incomplete provider response")
            text = choice.get("delta", {}).get("content")
            if text is not None:
                if not isinstance(text, str) or (stop and text):
                    raise ValueError("invalid provider delta")
                size += len(text.encode())
                if size > AI_TEXT_LIMIT:
                    raise ValueError("provider response too large")
                has_text |= bool(text.strip())
                if text:
                    yield text
            stop |= reason == "stop"
    if not has_text or not (done or stop):
        raise ValueError("incomplete provider stream")


def capabilities():
    engines_available = engines.available()
    alternate_pdf = pdf_support.available()
    pdf_view = engines_available["pdf"] or alternate_pdf
    ocr = engines.ocr_languages() if pdf_view else []
    return {"version": VERSION, "engines": engines_available, "limits": {"uploadBytes": engines.LIMIT},
            "operations": {
                "word": ["open-text", "replace-text", "edit-docx-body"] + (["extract-office-text", "export-new-document"] if engines_available["word"] else []),
                "sheet": ["preview-delimited", "edit-delimited"] + (["preview-office", "recalculate-preview", "save-xlsx", "insert-chart", "render-html"] if engines_available["grid"] else []),
                "slides": ["preview-text", "edit-text", "edit-speaker-notes"] + (["render", "roundtrip", "from-outline", "append-outline"] if engines_available["deck"] else []),
                "pdf": (["open", "render"] if pdf_view else [])
                       + (["open-save"] if engines_available["pdf"] else [])
                       + (["encrypted-view", "page-copy", "text-note"] if alternate_pdf else [])
                       + (["ocr"] if ocr else []),
            }, "aiConfigured": settings()["configured"], "aiStreaming": True, "ocr": bool(ocr), "ocrLanguages": ocr, "pdfPageCopy": alternate_pdf}


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(20)
        super().setup()

    def check_origin(self):
        if self.headers.get("Host") != "127.0.0.1:4173" or self.headers.get("Origin") not in (None, ORIGIN):
            raise engines.RequestError("Akses hanya dari origin loopback Ruangkerja.", 403)
        if self.headers.get("Sec-Fetch-Site") not in (None, "none", "same-origin"):
            raise engines.RequestError("Permintaan lintas situs ditolak.", 403)

    def send(self, result, status=200):
        if isinstance(result, dict):
            data, mime, filename = json.dumps(result, ensure_ascii=False).encode(), "application/json; charset=utf-8", None
        else:
            data, mime, filename = result
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.respond(self.get)

    def do_POST(self):
        self.respond(self.post)

    def respond(self, handler):
        try:
            self.check_origin()
            result = handler(urlsplit(self.path).path)
            if result is not None:
                self.send(result)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except (engines.RequestError, pdf_support.PdfError) as exc:
            self.send({"error": str(exc)}, exc.status)
        except (OSError, KeyError, IndexError, TypeError, ValueError, BadZipFile, ExpatError):
            self.send({"error": "Format file atau parameter operasi tidak valid."}, 422)

    def get(self, path):
        if path == "/api/ai/settings":
            return settings()
        if path == "/api/engine/capabilities":
            return capabilities()
        if path == "/api/health":
            return {"status": "ok", **capabilities()}
        if path.lstrip("/") in STATIC:
            file = ROOT / (path.lstrip("/") or "index.html")
            return file.read_bytes(), mimetypes.guess_type(file)[0] or "application/octet-stream", None
        raise engines.RequestError("Halaman tidak ditemukan.", 404)

    def read_body(self, limit):
        size = int(self.headers.get("Content-Length", "0"))
        if self.headers.get("Transfer-Encoding") or size < 0 or size > limit:
            raise engines.RequestError("Ukuran permintaan melewati batas.", 413)
        self.connection.settimeout(20)
        data = self.rfile.read(size)
        if len(data) != size:
            raise engines.RequestError("Permintaan belum lengkap.")
        return data

    def post(self, path):
        global SESSION
        if path == "/api/ai/settings/reset":
            with SESSION_WRITE:
                SESSION = None
                return settings()
        if path == "/api/ai/check":
            if not STREAM_SLOTS.acquire(blocking=False):
                raise engines.RequestError("Provider sedang digunakan. Coba lagi setelah permintaan selesai.", 429)
            try:
                generate({"task": "Connection check", "input": "Reply briefly with OK.", "language": "English"})
                return {"reachable": True}
            finally:
                STREAM_SLOTS.release()
        if path in ("/api/ai/settings", "/api/ai/generate", "/api/ai/stream"):
            if self.headers.get_content_type() != "application/json":
                raise engines.RequestError("Permintaan AI harus memakai JSON.", 415)
            data = json.loads(self.read_body(256 * 1024))
            if not isinstance(data, dict):
                raise engines.RequestError("Objek JSON diperlukan.")
            if path.endswith("/generate"):
                return generate(data)
            if path.endswith("/stream"):
                return self.stream(provider_request(data, stream=True))
            with SESSION_WRITE:
                previous, _ = active_provider()
                url, model, key = provider(data.get("url"), data.get("model"),
                                           "" if data.get("clearApiKey") is True else data.get("apiKey", ""))
                if not key and data.get("clearApiKey") is not True and url == previous[0]:
                    key = previous[2]
                SESSION = url, model, key
                return settings()
        route = re.fullmatch(r"/api/engine/(word|sheet|slides|pdf)/([a-z0-9/-]+)", path)
        if not route:
            raise engines.RequestError("Endpoint tidak ditemukan.", 404)
        if self.headers.get_content_type() != "multipart/form-data":
            raise engines.RequestError("Unggahan harus memakai multipart/form-data.", 415)
        kind, operation = route.groups()
        if not UPLOAD_SLOTS.acquire(blocking=False):
            raise engines.RequestError("Dua file sedang diproses. Coba lagi setelah salah satunya selesai.", 429)
        try:
            return self.upload(kind, operation)
        finally:
            UPLOAD_SLOTS.release()

    def stream(self, request):
        if not STREAM_SLOTS.acquire(blocking=False):
            raise engines.RequestError("Dua permintaan AI sedang berjalan. Coba lagi setelah salah satunya selesai.", 429)
        try:
            try:
                upstream = build_opener(NoRedirect()).open(request, timeout=45)
            except PROVIDER_FAILURES as exc:
                raise engines.RequestError(AI_ERROR, 502) from exc
            with upstream:
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True
                def emit(event):
                    self.wfile.write((json.dumps(event, ensure_ascii=False) + "\n").encode())
                    self.wfile.flush()

                deltas = iter(response_deltas(upstream))
                while True:
                    try:
                        text = next(deltas)
                    except StopIteration:
                        emit({"done": True})
                        break
                    except PROVIDER_FAILURES:
                        emit({"error": AI_ERROR})
                        break
                    emit({"delta": text})
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass
        finally:
            STREAM_SLOTS.release()

    def upload(self, kind, operation):
        header = self.headers["Content-Type"].encode("ascii")
        body = self.read_body(engines.LIMIT + 256 * 1024)
        message = BytesParser(policy=policy.default).parsebytes(b"Content-Type: " + header + b"\r\n\r\n" + body)
        fields = {}
        document = None
        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition")
            payload = part.get_payload(decode=True)
            if not isinstance(payload, bytes) or not name or name in fields or (name == "file" and document is not None):
                raise engines.RequestError("Form unggah tidak valid.")
            if name == "file":
                suffix = Path(part.get_filename() or "").suffix.lower()
                if suffix not in engines.FORMATS[kind] or (kind == "slides" and (suffix == ".md") != (operation == "from-outline")):
                    raise engines.RequestError("Ekstensi file tidak didukung untuk operasi ini.")
                if len(payload) > engines.LIMIT:
                    raise engines.RequestError("File lebih besar dari 64 MiB.", 413)
                document = suffix, payload
            else:
                fields[name] = payload.decode("utf-8")
        if document is None:
            raise engines.RequestError("Pilih file terlebih dahulu.")
        suffix, payload = document
        with TemporaryDirectory(prefix="ruangkerja-") as folder:
            source = Path(folder) / ("source" + suffix)
            output = Path(folder) / ("hasil-ruangkerja" + suffix)
            source.write_bytes(payload)
            adapter = ADAPTERS[kind]
            if kind == "slides":
                return adapter(operation, source, output, fields, fields.get("outline"))
            return adapter(operation, source, output, fields)


if __name__ == "__main__":
    with ThreadingHTTPServer(("127.0.0.1", 4173), Handler) as server:
        print("Ruangkerja siap di " + ORIGIN, flush=True)
        server.serve_forever()
