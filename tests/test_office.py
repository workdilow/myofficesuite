import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import engines
import host
from slides import append_slides, edit_slides, preview_slides


class LocalOfficeTests(unittest.TestCase):
    def test_csv_preview_uses_unsaved_edit_without_overwriting_source(self):
        with TemporaryDirectory() as folder, patch("engines.available", return_value={"grid": False}):
            source, output = (Path(folder) / name for name in ("input.csv", "output.csv"))
            source.write_text("1,2\n3,4\n")
            result = engines.sheet("preview-current", source, output, {
                "changes": '[{"sheet":"Sheet1","address":"B2","input":"8"}]'
            })["workbook"]
            self.assertEqual(result["values"], [["1", "2"], ["3", "8"]])
            self.assertEqual(result["range"], "A1:B2")
            self.assertEqual(source.read_text(), "1,2\n3,4\n")

    def test_writer_text_save(self):
        with TemporaryDirectory() as folder:
            source, output = (Path(folder) / name for name in ("input.txt", "output.txt"))
            source.write_text("Before")
            self.assertEqual(engines.word("open", source, output, {}), {"text": "Before"})
            data, _, _ = engines.word("replace", source, output, {"text": "Sesudah"})
            self.assertEqual(data, b"Sesudah")
            self.assertEqual(source.read_text(), "Before")

    def test_pdf_preview_preserves_page_numbers_for_quotes(self):
        with patch("engines.shutil.which", return_value="pdfcraft-cli"), patch("engines.pdf_support.handle", return_value=None), patch("engines.run", side_effect=['{"pages":3}', "satu", "", "tiga"]):
            preview = engines.pdf("open", Path("sample.pdf"), Path("output.pdf"), {})
        self.assertEqual(preview["pageTexts"], ["satu", "", "tiga"])
        self.assertIn("--- Halaman 3 ---\ntiga", preview["text"])

    def test_provider_url_and_secret_visibility(self):
        with self.assertRaises(engines.RequestError):
            host.provider("http://remote.example/api", "model", "secret")
        with patch("host.SESSION", host.provider("http://127.0.0.1:11434/v1/chat/completions", "model", "secret")):
            reply = host.settings()
            self.assertTrue(reply["hasApiKey"])
            self.assertNotIn("secret", str(reply))


@unittest.skipUnless(importlib.util.find_spec("pptx"), "python-pptx is optional")
class SlidesTests(unittest.TestCase):
    def test_append_with_edits_retains_original_notes_theme_and_slide_order(self):
        from pptx import Presentation
        with TemporaryDirectory() as folder:
            source, draft, output, edited = (Path(folder) / name for name in
                                              ("source.pptx", "draft.pptx", "result.pptx", "edited.pptx"))
            deck = Presentation()
            first = deck.slides.add_slide(deck.slide_layouts[1])
            first.shapes.title.text = "Asli"
            first.notes_slide.notes_text_frame.text = "Catatan pembicara tetap di sini"
            second = deck.slides.add_slide(deck.slide_layouts[1])
            second.shapes.title.text = "Kedua"
            deck.save(source)
            new = Presentation()
            new.slides.add_slide(new.slide_layouts[1]).shapes.title.text = "Outline baru"
            new.save(draft)
            preview = preview_slides(source)
            edits = [{"slide": 1, "shapeId": preview["slides"][1]["shapes"][0]["id"], "text": "Kedua diedit"}]
            append_slides(source, draft, output, edits)
            edit_slides(source, edited, edits)
            reopened = Presentation(output)
            self.assertEqual([slide.shapes.title.text for slide in reopened.slides], ["Asli", "Kedua diedit", "Outline baru"])
            self.assertEqual(reopened.slides[0].notes_slide.notes_text_frame.text, "Catatan pembicara tetap di sini")
            self.assertEqual(Presentation(edited).slides[1].shapes.title.text, "Kedua diedit")
            with ZipFile(source) as old, ZipFile(output) as current:
                for name in set(old.namelist()) - {
                    "ppt/presentation.xml", "ppt/_rels/presentation.xml.rels", "[Content_Types].xml", "ppt/slides/slide2.xml"
                }:
                    self.assertEqual(current.read(name), old.read(name), name)
            self.assertEqual(Presentation(source).slides[1].shapes.title.text, "Kedua")

    def test_speaker_notes_edit_preserves_slide_content_and_unrelated_parts(self):
        from pptx import Presentation

        with TemporaryDirectory() as folder:
            source, output = [Path(folder) / name for name in ("source.pptx", "edited.pptx")]
            deck = Presentation()
            slide = deck.slides.add_slide(deck.slide_layouts[1])
            slide.shapes.title.text = "Original title"
            slide.notes_slide.notes_text_frame.text = "Catatan lama"
            deck.slides.add_slide(deck.slide_layouts[1])
            deck.save(source)
            preview = preview_slides(source)
            self.assertEqual(preview["slides"][0]["notes"], "Catatan lama")
            self.assertIsNone(preview["slides"][1]["notes"])
            edit_slides(source, output, [{"slide": 0, "kind": "notes", "text": "Catatan baru\nBaris kedua"}])
            reopened = Presentation(output)
            self.assertEqual(reopened.slides[0].notes_slide.notes_text_frame.text, "Catatan baru\nBaris kedua")
            self.assertEqual(reopened.slides[0].shapes.title.text, "Original title")
            with ZipFile(source) as old, ZipFile(output) as new:
                differences = [name for name in old.namelist() if old.read(name) != new.read(name)]
            self.assertEqual(differences, ["ppt/notesSlides/notesSlide1.xml"])
