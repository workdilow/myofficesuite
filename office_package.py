"""Bounded reads and part-preserving writes for Office ZIP containers."""
from xml.dom import minidom
from zipfile import ZIP_DEFLATED, ZipFile


class XmlPackage:
    def __init__(self, archive):
        self.archive = archive
        self.updates = {}
        names = archive.namelist()
        if len(names) != len(set(names)) or len(names) > 12000:
            raise ValueError("Entri Office ganda atau melebihi batas.")
        if sum(member.file_size for member in archive.infolist()) > 128 * 1024 * 1024:
            raise ValueError("Office melebihi batas ukuran dekompresi 128 MiB.")
        self.names = set(names)

    def xml(self, part):
        data = self.updates.get(part)
        if data is None:
            data = self.archive.read(part)
        if len(data) > 8 * 1024 * 1024 or b"\x00" in data or b"<!doctype" in data.lower():
            raise ValueError("Bagian XML Office tidak didukung atau melebihi batas.")
        return minidom.parseString(data).documentElement

    def update(self, part, element):
        self.updates[part] = element.ownerDocument.toxml(encoding="UTF-8")

    def write(self, output):
        if any(name.lower().startswith("_xmlsignatures/") for name in self.names):
            raise ValueError("Office bertanda tangan perlu disimpan ulang tanpa tanda tangan sebelum diedit.")
        with ZipFile(output, "w", ZIP_DEFLATED) as result:
            for name in self.archive.namelist():
                if name not in self.updates:
                    result.writestr(name, self.archive.read(name))
            for name, data in self.updates.items():
                result.writestr(name, data)

