import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

import engines


@unittest.skipUnless(importlib.util.find_spec("docx"), "python-docx is optional")
class WordDocumentTests(unittest.TestCase):
    def setUp(self):
        from docx import Document

        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.source = Path(folder.name) / "source.docx"
        self.output = Path(folder.name) / "edited.docx"
        document = Document()
        document.sections[0].header.paragraphs[0].text = "Project header"
        first = document.add_paragraph(style="Heading 1")
        first.add_run("Annual ").bold = True
        first.add_run("report").italic = True
        document.add_table(rows=1, cols=1).cell(0, 0).text = "Table entry"
        document.add_paragraph("Original footer note")
        document.add_paragraph("Protected tab\tvalue")
        document.save(self.source)

    def save(self, text):
        return engines.word("replace", self.source, self.output, {"text": text})

    def test_body_edits_preserve_heading_runs_header_and_table(self):
        from docx import Document

        opened = engines.word("open", self.source, self.output, {})["text"]
        self.assertEqual(opened, "Annual report\nOriginal footer note\nProtected tab value")
        source_bytes = self.source.read_bytes()
        self.save("Annual summary\nUpdated footer note\nProtected tab value")
        doc = Document(self.output)
        self.assertEqual(doc.paragraphs[0].text, "Annual summary")
        self.assertEqual(doc.paragraphs[0].style.name, "Heading 1")
        self.assertTrue(doc.paragraphs[0].runs[0].bold)
        self.assertTrue(doc.paragraphs[0].runs[1].italic)
        self.assertEqual(doc.paragraphs[0].runs[1].text, "summary")
        self.assertEqual(doc.tables[0].cell(0, 0).text, "Table entry")
        self.assertEqual(doc.sections[0].header.paragraphs[0].text, "Project header")
        with ZipFile(self.source) as original, ZipFile(self.output) as edited:
            self.assertEqual(set(original.namelist()), set(edited.namelist()))
            for name in set(original.namelist()) - {"word/document.xml"}:
                self.assertEqual(original.read(name), edited.read(name), name)
        self.assertEqual(self.source.read_bytes(), source_bytes)

    def test_structured_edit_fails_without_a_partial_output(self):
        with self.assertRaisesRegex(engines.RequestError, "tab"):
            self.save("Annual report\nOriginal footer note\nChanged tab")
        self.assertFalse(self.output.exists())

    def test_inserts_and_deletes_simple_paragraphs(self):
        from docx import Document

        self.save("Annual report\nNew paragraph\nAnother paragraph\nProtected tab value")
        self.assertEqual([p.text for p in Document(self.output).paragraphs], [
            "Annual report", "New paragraph", "Another paragraph", "Protected tab\tvalue",
        ])
