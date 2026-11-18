import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import engines
import pdf_support


@unittest.skipUnless(pdf_support.available() and importlib.util.find_spec("pypdf") and
                     importlib.util.find_spec("reportlab"), "PDF fixtures need optional libraries")
class PdfTests(unittest.TestCase):
    def setUp(self):
        from reportlab.pdfgen.canvas import Canvas

        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        folder = temp.name
        self.source = Path(folder) / "source.pdf"
        self.output = Path(folder) / "copy.pdf"
        canvas = Canvas(str(self.source))
        for word in ("First page", "Second page", "Third page"):
            canvas.drawString(20, 700, word)
            canvas.showPage()
        canvas.save()

    def encrypt(self, password, *, copy=True):
        from pypdf import PdfWriter
        from pypdf.constants import UserAccessPermissions

        path = self.source.with_name("protected.pdf")
        writer = PdfWriter(clone_from=self.source)
        permissions = UserAccessPermissions.PRINT
        if copy:
            permissions |= UserAccessPermissions.EXTRACT
        writer.encrypt(password, "other-owner-password", permissions_flag=permissions, algorithm="AES-256")
        writer.write(path)
        writer.close()
        return path

    def test_correct_wrong_and_empty_password_without_cli(self):
        protected = self.encrypt("document-password")
        original = protected.read_bytes()
        with patch("engines.run", side_effect=AssertionError("credentials must not go to a CLI")):
            for password in ("", "wrong"):
                with self.assertRaises(pdf_support.PdfError) as error:
                    engines.pdf("open", protected, self.output, {"password": password})
                self.assertEqual(error.exception.status, 401)
            form = {"password": "document-password"}
            opened = engines.pdf("open", protected, self.output, form)
            self.assertEqual(opened["pageTexts"], ["First page", "Second page", "Third page"])
            self.assertTrue(opened["encrypted"])
            image, mime, _ = engines.pdf("page/2", protected, self.output, form)
            self.assertEqual(mime, "image/png")
            self.assertTrue(image.startswith(b"\x89PNG\r\n\x1a\n"))
            with self.assertRaisesRegex(pdf_support.PdfError, "terenkripsi"):
                engines.pdf("pages", protected, self.output, form | {"selection": "1"})
            with self.assertRaisesRegex(pdf_support.PdfError, "terenkripsi"):
                engines.pdf("ocr", protected, self.output, form)
        self.assertEqual(protected.read_bytes(), original)
        self.assertFalse(self.output.exists())

    def test_empty_password_still_preserves_encryption_and_copy_restriction(self):
        protected = self.encrypt("", copy=False)
        opened = engines.pdf("open", protected, self.output, {})
        self.assertTrue(opened["encrypted"])
        self.assertTrue(opened["copyRestricted"])
        self.assertEqual(opened["pageTexts"], [])
        with self.assertRaisesRegex(pdf_support.PdfError, "terenkripsi"):
            engines.pdf("ocr", protected, self.output, {})

    def test_extract_reorder_rotate_and_keep_original(self):
        from pypdf import PdfReader

        data = self.source.read_bytes()
        engines.pdf("pages", self.source, self.output, {"selection": "3,1", "rotation": "90"})
        pages = PdfReader(self.output).pages
        self.assertEqual([p.extract_text().strip() for p in pages], ["Third page", "First page"])
        self.assertEqual([p.rotation for p in pages], [90, 90])
        self.assertEqual(self.source.read_bytes(), data)
        for selection in ("2,2", "4", "2-1", "1,"):
            with self.assertRaises(pdf_support.PdfError):
                engines.pdf("pages", self.source, self.output, {"selection": selection})

    def test_note_is_saved_to_selected_page_only(self):
        from pypdf import PdfReader

        original = self.source.read_bytes()
        engines.pdf("note", self.source, self.output, {"page": "2", "text": "Periksa ulang ✓"})
        pages = PdfReader(self.output).pages
        self.assertNotIn("/Annots", pages[0])
        note = pages[1]["/Annots"][0].get_object()
        self.assertEqual(note["/Subtype"], "/Text")
        self.assertEqual(note["/Contents"], "Periksa ulang ✓")
        self.assertEqual(self.source.read_bytes(), original)

    def test_ocr_passes_selected_installed_model(self):
        def fake_ocr(command, *args, **kwargs):
            self.assertEqual(command, "ocrmypdf")
            self.assertEqual(args[:2], ("--language", "ind+eng"))
            args[-1].write_bytes(self.source.read_bytes())
        with patch("engines.ocr_languages", return_value=["eng", "ind", "ind+eng"]), patch(
            "engines.run", side_effect=fake_ocr
        ), patch("engines.shutil.which", return_value=None):
            _, mime, _ = engines.pdf("ocr", self.source, self.output, {"language": "ind+eng"})
        self.assertEqual(mime, "application/pdf")
