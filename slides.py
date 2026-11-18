"""Targeted PPTX edits which keep unrelated package members byte-for-byte."""
import posixpath
from xml.dom import Node, minidom
from zipfile import ZIP_DEFLATED, ZipFile

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
PRESENTATION = "ppt/presentation.xml"
MIME = "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"


def children(node, ns, name):
    return [el for el in node.childNodes if el.nodeType == Node.ELEMENT_NODE
            and el.namespaceURI == ns and el.localName == name]


def first(node, ns, name):
    return next(iter(children(node, ns, name)), None)


def add(node, ns, name, **attributes):
    prefix = node.prefix if node.namespaceURI == ns else "rka"
    element = node.ownerDocument.createElementNS(ns, f"{prefix}:{name}" if prefix else name)
    if node.namespaceURI != ns:
        element.setAttributeNS("http://www.w3.org/2000/xmlns/", "xmlns:rka", ns)
    for key, value in attributes.items():
        element.setAttribute(key, str(value))
    node.appendChild(element)
    return element


def rels(part):
    return posixpath.join(posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels")


def target(part, relationship):
    value = relationship.getAttribute("Target")
    if relationship.getAttribute("TargetMode") == "External" or not value or ":" in value or "\\" in value:
        raise ValueError("Relasi internal PPTX tidak valid.")
    return posixpath.normpath(value.lstrip("/") if value.startswith("/") else
                              posixpath.join(posixpath.dirname(part), value))


class Package:
    def __init__(self, archive):
        self.archive = archive
        self.updates = {}
        names = archive.namelist()
        if len(names) != len(set(names)) or len(names) > 12000:
            raise ValueError("Entri PPTX ganda atau melebihi batas.")
        if sum(member.file_size for member in archive.infolist()) > 128 * 1024 * 1024:
            raise ValueError("PPTX melebihi batas ukuran dekompresi 128 MiB.")
        self.names = set(names)

    def xml(self, part):
        data = self.updates.get(part)
        if data is None:
            data = self.archive.read(part)
        if len(data) > 8 * 1024 * 1024 or b"\x00" in data or b"<!doctype" in data.lower():
            raise ValueError("Bagian XML PPTX tidak didukung atau melebihi batas.")
        return minidom.parseString(data).documentElement

    def update(self, part, element):
        self.updates[part] = element.ownerDocument.toxml(encoding="UTF-8")

    def links(self, part):
        return children(self.xml(rels(part)), REL, "Relationship")

    def deck(self):
        root = self.xml(PRESENTATION)
        listing = first(root, P, "sldIdLst")
        links = {link.getAttribute("Id"): link for link in self.links(PRESENTATION)
                 if link.getAttribute("Type") == R + "/slide"}
        slides = [(entry, target(PRESENTATION, links[entry.getAttributeNS(R, "id")]))
                  for entry in children(listing, P, "sldId")] if listing is not None else []
        return listing, slides

    def write(self, output):
        if any(name.lower().startswith("_xmlsignatures/") for name in self.names):
            raise ValueError("PPTX bertanda tangan perlu disimpan ulang tanpa tanda tangan sebelum diedit.")
        with ZipFile(output, "w", ZIP_DEFLATED) as result:
            for name in self.archive.namelist():
                if name not in self.updates:
                    result.writestr(name, self.archive.read(name))
            for name, data in self.updates.items():
                result.writestr(name, data)


def text_shapes(slide):
    for shape in slide.getElementsByTagNameNS(P, "sp"):
        nv = first(shape, P, "nvSpPr")
        props = first(nv, P, "cNvPr") if nv is not None else None
        body = first(shape, P, "txBody")
        if props is not None and props.getAttribute("id").isdecimal() and body is not None:
            yield int(props.getAttribute("id")), props.getAttribute("name"), body


def paragraphs(body):
    return children(body, A, "p")


def preview_slides(source):
    with ZipFile(source) as archive:
        package = Package(archive)
        _, slides = package.deck()
        if not slides:
            raise ValueError("Presentasi kosong.")
        preview = []
        for index, (_, part) in enumerate(slides[:40]):
            shapes = []
            for shape_id, name, body in text_shapes(package.xml(part)):
                value = "\n".join("".join(el.firstChild.data for el in para.getElementsByTagNameNS(A, "t")
                                          if el.firstChild) for para in paragraphs(body))
                shapes.append({"id": shape_id, "name": name, "text": value[:12000]})
            preview.append({"index": index, "name": f"Slide {index + 1}", "shapes": shapes})
        return {"slideCount": len(slides), "slides": preview, "truncated": len(slides) > len(preview)}


def replace_text(body, text):
    original = paragraphs(body)
    for index, line in enumerate(text.split("\n")):
        if index < len(original):
            para = original[index]
        elif original:
            para = original[-1].cloneNode(deep=True)
            body.appendChild(para)
        else:
            para = add(body, A, "p")
        runs = children(para, A, "r")
        run = runs[0] if runs else add(para, A, "r")
        for item in list(para.childNodes):
            if item.nodeType == Node.ELEMENT_NODE and item.namespaceURI == A and item.localName in ("r", "br", "fld") and item is not run:
                para.removeChild(item)
        value = first(run, A, "t")
        if value is None:
            value = add(run, A, "t")
        while value.firstChild:
            value.removeChild(value.firstChild)
        value.appendChild(value.ownerDocument.createTextNode(line))
        end = first(para, A, "endParaRPr")
        if end is not None:
            para.insertBefore(run, end)
    for extra in original[len(text.split("\n")):]:
        body.removeChild(extra)


def apply_edits(package, slides, entries):
    modified = {}
    for entry in entries:
        index, shape_id, text = entry["slide"], entry["shapeId"], entry["text"]
        if type(index) is not int or not 0 <= index < len(slides) or type(shape_id) is not int or not isinstance(text, str) or len(text) > 12000:
            raise ValueError("Edit teks slide tidak valid.")
        part = slides[index][1]
        if part not in modified:
            modified[part] = package.xml(part)
        slide = modified[part]
        for key, _, body in text_shapes(slide):
            if key == shape_id:
                replace_text(body, text)
                break
        else:
            raise ValueError("Objek teks slide tidak ditemukan.")
    for part, slide in modified.items():
        package.update(part, slide)


def edit_slides(source, output, entries):
    with ZipFile(source) as archive:
        package = Package(archive)
        _, slides = package.deck()
        apply_edits(package, slides, entries)
        package.write(output)


def related(package, part, kind):
    return [target(part, link) for link in package.links(part) if link.getAttribute("Type") == R + "/" + kind]


def append_slides(source, generated, output, entries):
    with ZipFile(source) as original, ZipFile(generated) as drafted:
        package, draft = Package(original), Package(drafted)
        listing, slides = package.deck()
        _, imports = draft.deck()
        if not slides or not 1 <= len(imports) <= 30:
            raise ValueError("Presentasi sumber harus memiliki slide. Outline dibatasi 1–30 slide.")
        # Use the master of the last slide and its Title and Content layout.
        current_layout, = related(package, slides[-1][1], "slideLayout")
        master, = related(package, current_layout, "slideMaster")
        layouts = related(package, master, "slideLayout")
        layout = next((part for part in [current_layout, *layouts]
                       if package.xml(part).getAttribute("type") == "obj"), None)
        if layout is None:
            raise ValueError("Master slide terakhir memerlukan layout Title and Content.")
        apply_edits(package, slides, entries)
        presentation_rels = package.xml(rels(PRESENTATION))
        content_types = package.xml("[Content_Types].xml")
        ids = {link.getAttribute("Id") for link in children(presentation_rels, REL, "Relationship")}
        slide_id = max(255, *(int(entry.getAttribute("id")) for entry, _ in slides))
        for i, (_, part) in enumerate(imports, 1):
            if any(link.getAttribute("Type") != R + "/slideLayout" for link in draft.links(part)):
                raise ValueError("Slide hasil outline memuat dependensi selain layout.")
            slide = draft.xml(part)
            if any(attr.namespaceURI == R for node in [slide, *slide.getElementsByTagName("*")]
                   for attr in node.attributes.values()):
                raise ValueError("Slide hasil outline memuat relasi objek eksternal.")
            number = i
            while True:
                new_part = f"ppt/slides/ruangkerja{number}.xml"
                rid = f"rIdRuangkerja{number}"
                if new_part not in package.names and rels(new_part) not in package.names and rid not in ids:
                    break
                number += 1
            ids.add(rid)
            slide_id += 1
            if slide_id >= 2147483648:
                raise ValueError("ID slide baru melampaui batas PPTX.")
            entry = add(listing, P, "sldId", id=slide_id)
            entry.setAttributeNS("http://www.w3.org/2000/xmlns/", "xmlns:rkrel", R)
            entry.setAttributeNS(R, "rkrel:id", rid)
            add(presentation_rels, REL, "Relationship", Id=rid, Type=R + "/slide",
                Target=posixpath.relpath(new_part, "ppt"))
            add(content_types, CT, "Override", PartName="/" + new_part, ContentType=MIME)
            slide_rels = minidom.getDOMImplementation().createDocument(REL, "Relationships", None).documentElement
            slide_rels.setAttribute("xmlns", REL)
            add(slide_rels, REL, "Relationship", Id="rId1", Type=R + "/slideLayout",
                Target=posixpath.relpath(layout, posixpath.dirname(new_part)))
            package.update(rels(new_part), slide_rels)
            package.update(new_part, slide)
        package.update(PRESENTATION, listing)
        package.update(rels(PRESENTATION), presentation_rels)
        package.update("[Content_Types].xml", content_types)
        package.write(output)
