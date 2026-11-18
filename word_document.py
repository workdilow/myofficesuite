"""Edit body text within DOCX while preserving all unrelated package members."""
from bisect import bisect_right
from difflib import SequenceMatcher
from xml.dom import Node
from zipfile import ZipFile

from office_package import XmlPackage

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML = "http://www.w3.org/XML/1998/namespace"
PART = "word/document.xml"
MAX_PARAGRAPHS = 2000
MAX_TEXT_BYTES = 256 * 1024


class EditError(ValueError):
    pass


def elements(node):
    return [child for child in node.childNodes if child.nodeType == Node.ELEMENT_NODE]


def is_word(node, name):
    return node.namespaceURI == W and node.localName == name


def only(node, allowed):
    return all(child.namespaceURI == W and child.localName in allowed for child in elements(node))


def text_nodes(paragraph):
    for child in elements(paragraph):
        if is_word(child, "r"):
            yield from elements(child)
        elif is_word(child, "hyperlink"):
            yield from text_nodes(child)


def text_of(node):
    return "".join(child.data for child in node.childNodes if child.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE))


def paragraph_text(paragraph):
    visible = []
    for node in text_nodes(paragraph):
        if is_word(node, "t"):
            visible.append(text_of(node))
        elif node.namespaceURI == W and node.localName in {"tab", "br", "cr"}:
            visible.append(" ")
    return "".join(visible)


def read_package(package):
    root = package.xml(PART)
    body = next((node for node in elements(root) if is_word(node, "body")), None)
    if body is None or not is_word(root, "document"):
        raise EditError("Bagian utama DOCX tidak didukung.")
    paragraphs = [node for node in elements(body) if is_word(node, "p")]
    lines = [paragraph_text(para) for para in paragraphs]
    if len(lines) > MAX_PARAGRAPHS or len("\n".join(lines).encode()) > MAX_TEXT_BYTES:
        raise EditError("Editor DOCX mendukung hingga 2.000 paragraf dan 256 KiB teks isi.")
    return body, paragraphs, lines


def open_text(source):
    with ZipFile(source) as archive:
        _, _, lines = read_package(XmlPackage(archive))
        return "\n".join(lines)


def require_simple(paragraph, *, structural):
    if not only(paragraph, {"pPr", "r"}):
        raise EditError("Paragraf berisi tautan, bookmark, atau struktur Word lain yang harus dipertahankan.")
    for node in elements(paragraph):
        if is_word(node, "r") and not only(node, {"rPr", "t"}):
            raise EditError("Paragraf berisi objek, bidang, tab, atau pemisah yang harus dipertahankan.")
        if is_word(node, "pPr"):
            has_section_break = any(is_word(child, "sectPr") for child in elements(node))
            supported_structure = only(node, {"pStyle", "spacing", "jc", "ind", "rPr"})
            if has_section_break or (structural and not supported_structure):
                raise EditError("Struktur paragraf ini perlu disunting melalui WordCraft.")


def create(parent, name):
    root = parent.ownerDocument
    prefix = parent.prefix
    return root.createElementNS(W, f"{prefix}:{name}" if prefix else name)


def write_text(node, value):
    while node.firstChild:
        node.removeChild(node.firstChild)
    node.appendChild(node.ownerDocument.createTextNode(value))
    if value != value.strip():
        node.setAttributeNS(XML, "xml:space", "preserve")


def append_text(paragraph, value):
    node = create(paragraph, "r")
    text_node = create(node, "t")
    write_text(text_node, value)
    node.appendChild(text_node)
    paragraph.appendChild(node)


def changes(before, after):
    if max(len(before), len(after)) <= 4096:
        return [op[1:] for op in SequenceMatcher(None, before, after).get_opcodes() if op[0] != "equal"]
    head = 0
    while head < min(len(before), len(after)) and before[head] == after[head]:
        head += 1
    tail = 0
    while tail < min(len(before), len(after)) - head and before[-tail - 1] == after[-tail - 1]:
        tail += 1
    return [(head, len(before) - tail, head, len(after) - tail)]


def edit_text(paragraph, before, after):
    if before == after:
        return
    require_simple(paragraph, structural=False)
    nodes = [node for node in text_nodes(paragraph) if is_word(node, "t")]
    if not nodes:
        append_text(paragraph, after)
        return
    runs = [text_of(node) for node in nodes]
    offsets = []
    offset = 0
    for run in runs:
        offsets.append(offset)
        offset += len(run)
    for start, stop, new_start, new_stop in reversed(changes(before, after)):
        # Insert text with the format at the edit position, retaining all other text runs.
        first = bisect_right(offsets, start) - 1
        last = bisect_right(offsets, stop - 1) - 1 if stop > start else first
        replacement = after[new_start:new_stop]
        if first == last:
            runs[first] = runs[first][:start - offsets[first]] + replacement + runs[first][stop - offsets[first]:]
        else:
            runs[first] = runs[first][:start - offsets[first]] + replacement
            runs[last] = runs[last][stop - offsets[last]:]
            runs[first + 1:last] = [""] * (last - first - 1)
    for node, run in zip(nodes, runs):
        if text_of(node) != run:
            write_text(node, run)


def neighbor(node, direction):
    while node is not None:
        node = getattr(node, direction)
        if node is not None and node.nodeType == Node.ELEMENT_NODE:
            return node
    return None


def resize(body, paragraphs, start, stop, inserted):
    if stop > start:
        for index in range(start, stop):
            require_simple(paragraphs[index], structural=True)
            if index > start and neighbor(paragraphs[index - 1], "nextSibling") is not paragraphs[index]:
                raise EditError("Pemisah paragraf di sekitar tabel atau blok Word perlu disunting melalui WordCraft.")
    following = paragraphs[start] if start < len(paragraphs) else (
        neighbor(paragraphs[-1], "nextSibling") if paragraphs else next(iter(elements(body)), None))
    if inserted and start == stop and 0 < start < len(paragraphs):
        if neighbor(paragraphs[start - 1], "nextSibling") is not following:
            raise EditError("Penempatan paragraf baru di sekitar tabel perlu disunting melalui WordCraft.")
    for value in inserted:
        paragraph = create(body, "p")
        append_text(paragraph, value)
        body.insertBefore(paragraph, following)
    for paragraph in paragraphs[start:stop]:
        body.removeChild(paragraph)


def save_text(source, output, text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if any(ord(char) < 32 and char != "\n" or char in "\ufffe\uffff" for char in text):
        raise EditError("Gunakan teks biasa dan pemisah paragraf pada editor DOCX.")
    if len(text.encode()) > MAX_TEXT_BYTES or text.count("\n") >= MAX_PARAGRAPHS:
        raise EditError("Edit DOCX dibatasi hingga 2.000 paragraf dan 256 KiB.")
    with ZipFile(source) as archive:
        package = XmlPackage(archive)
        body, paragraphs, before = read_package(package)
        if "word/settings.xml" in package.names:
            for protection in package.xml("word/settings.xml").getElementsByTagNameNS(W, "documentProtection"):
                if protection.getAttributeNS(W, "enforcement") not in ("", "false", "0", "off"):
                    raise EditError("DOCX ini mengaktifkan batas penyuntingan di Word.")
        after = text.split("\n")
        if text == "\n".join(before):
            package.write(output)
            return
        for action, start, stop, new_start, new_stop in SequenceMatcher(None, before, after, autojunk=False).get_opcodes():
            if action == "equal":
                continue
            overlap = min(stop - start, new_stop - new_start)
            if overlap != stop - start or overlap != new_stop - new_start:
                resize(body, paragraphs, start + overlap, stop, after[new_start + overlap:new_stop])
            for offset in range(overlap):
                edit_text(paragraphs[start + offset], before[start + offset], after[new_start + offset])
        package.update(PART, body)
        package.write(output)
