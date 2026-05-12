from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


TEI_NS = "http://www.tei-c.org/ns/1.0"
NS = {"tei": TEI_NS}


@dataclass
class GrobidSections:
    title: str | None = None
    abstract: str | None = None
    authors: list[str] = field(default_factory=list)
    sections: list[dict[str, str]] = field(default_factory=list)
    references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "abstract": self.abstract,
            "authors": self.authors,
            "sections": self.sections,
            "references": self.references,
        }


def grobid_url() -> str | None:
    return os.environ.get("GROBID_URL")


def fetch_tei(pdf_path: Path, url: str, timeout: float = 60.0) -> str | None:
    endpoint = url.rstrip("/") + "/api/processFulltextDocument"
    boundary = "----paperharness"
    body = _multipart_body(pdf_path, boundary)
    request = Request(
        endpoint,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Accept": "application/xml"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return None
            return response.read().decode("utf-8", errors="ignore")
    except (URLError, TimeoutError, ConnectionError):
        return None


def parse_tei(xml_text: str) -> GrobidSections:
    root = ET.fromstring(xml_text)
    out = GrobidSections()
    title_el = root.find(".//tei:titleStmt/tei:title", NS)
    if title_el is not None and title_el.text:
        out.title = title_el.text.strip()
    abstract_el = root.find(".//tei:abstract", NS)
    if abstract_el is not None:
        out.abstract = _collect_text(abstract_el).strip() or None
    for author in root.findall(".//tei:sourceDesc//tei:author/tei:persName", NS):
        name_parts = [el.text for el in author if el.text]
        if name_parts:
            out.authors.append(" ".join(part.strip() for part in name_parts if part))
    body = root.find(".//tei:text/tei:body", NS)
    if body is not None:
        for div in body.findall("tei:div", NS):
            head_el = div.find("tei:head", NS)
            head = head_el.text.strip() if head_el is not None and head_el.text else None
            text = _collect_text(div, skip_tag="head").strip()
            if head or text:
                out.sections.append({"head": head or "", "text": text})
    for ref in root.findall(".//tei:listBibl/tei:biblStruct", NS):
        label = _collect_text(ref).strip()
        if label:
            out.references.append(label[:400])
    return out


def extract_sections(pdf_path: Path, url: str | None = None) -> GrobidSections | None:
    url = url or grobid_url()
    if not url:
        return None
    tei = fetch_tei(pdf_path, url)
    if not tei:
        return None
    try:
        return parse_tei(tei)
    except ET.ParseError:
        return None


def _multipart_body(pdf_path: Path, boundary: str) -> bytes:
    data = pdf_path.read_bytes()
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="input"; filename="{pdf_path.name}"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    return head + data + tail


def _collect_text(element: ET.Element, skip_tag: str | None = None) -> str:
    parts: list[str] = []
    for node in element.iter():
        tag = node.tag.split("}", 1)[-1]
        if skip_tag and tag == skip_tag:
            continue
        if node.text:
            parts.append(node.text)
        if node.tail:
            parts.append(node.tail)
    return " ".join(p.strip() for p in parts if p and p.strip())
