"""Deterministic parsers for the first ThoughtHarbor ingestion formats."""

import re
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import PurePath
from typing import Any, BinaryIO, Protocol

from docx import Document as DocxDocument
from pypdf import PdfReader


class ParserError(Exception):
    """Raised when a supported file cannot produce usable normalized text."""


class UnsupportedFormatError(ParserError):
    """Raised when no parser is registered for the source format."""


@dataclass(frozen=True, slots=True)
class ParsedSection:
    """A citation-friendly section within normalized text."""

    text: str
    offset_start: int
    offset_end: int
    location: dict[str, object]


@dataclass(frozen=True, slots=True)
class ParsedContent:
    """Normalized text and parser metadata ready for persistence."""

    text: str
    sections: tuple[ParsedSection, ...]
    metadata: dict[str, object]
    parser_name: str
    parser_version: str


class ContentParser(Protocol):
    """Port implemented by format-specific parsers."""

    def parse(self, source: BinaryIO) -> ParsedContent: ...


def parse_content(source: BinaryIO, *, original_name: str, media_type: str | None) -> ParsedContent:
    """Choose a parser by safe metadata and return normalized, located text."""

    parser = _parser_for(original_name, media_type)
    result = parser.parse(source)
    if not result.text.strip() or not result.sections:
        raise ParserError("The file contains no extractable text")
    return result


@dataclass(frozen=True, slots=True)
class _PlainTextParser:
    name: str = "plain_text"
    version: str = "1"

    def parse(self, source: BinaryIO) -> ParsedContent:
        text = _decode(source.read())
        normalized = _normalize(text)
        sections = _paragraph_sections(normalized)
        return ParsedContent(normalized, sections, {}, self.name, self.version)


@dataclass(frozen=True, slots=True)
class _PdfParser:
    name: str = "pypdf"
    version: str = "1"

    def parse(self, source: BinaryIO) -> ParsedContent:
        try:
            pages = [page.extract_text() or "" for page in PdfReader(source).pages]
        except Exception as error:
            raise ParserError("The PDF could not be read") from error
        text = "\n\n".join(_normalize(page).strip() for page in pages).strip()
        sections: list[ParsedSection] = []
        cursor = 0
        for page_number, page_text in enumerate(pages, start=1):
            normalized_page = _normalize(page_text).strip()
            if normalized_page:
                start = text.find(normalized_page, cursor)
                end = start + len(normalized_page)
                sections.append(ParsedSection(normalized_page, start, end, {"page": page_number}))
                cursor = end
        return ParsedContent(
            text, tuple(sections), {"page_count": len(pages)}, self.name, self.version
        )


@dataclass(frozen=True, slots=True)
class _DocxParser:
    name: str = "python_docx"
    version: str = "1"

    def parse(self, source: BinaryIO) -> ParsedContent:
        try:
            paragraphs = list(DocxDocument(source).paragraphs)
        except Exception as error:
            raise ParserError("The DOCX document could not be read") from error
        parts: list[str] = []
        locations: list[dict[str, object]] = []
        for paragraph in paragraphs:
            value = _normalize(paragraph.text).strip()
            if value:
                parts.append(value)
                style_name = paragraph.style.name if paragraph.style is not None else None
                locations.append({"paragraph": len(locations), "style": style_name})
        text = "\n\n".join(parts)
        sections = _sections_from_parts(text, parts, locations)
        return ParsedContent(
            text, sections, {"paragraph_count": len(paragraphs)}, self.name, self.version
        )


@dataclass(frozen=True, slots=True)
class _EmailParser:
    name: str = "email"
    version: str = "1"

    def parse(self, source: BinaryIO) -> ParsedContent:
        try:
            message = BytesParser(policy=policy.default).parse(source)
        except Exception as error:
            raise ParserError("The email could not be read") from error
        body = _email_body(message)
        normalized = _normalize(body)
        metadata: dict[str, object] = {
            "subject": message.get("subject"),
            "sender": message.get("from"),
            "recipients": [address for _, address in getaddresses(message.get_all("to", []))],
        }
        date = message.get("date")
        if date:
            try:
                metadata["sent_at"] = parsedate_to_datetime(date).isoformat()
            except (TypeError, ValueError, IndexError):
                metadata["sent_at"] = date
        return ParsedContent(
            normalized, _paragraph_sections(normalized), metadata, self.name, self.version
        )


def _parser_for(original_name: str, media_type: str | None) -> ContentParser:
    suffix = PurePath(original_name.casefold()).suffix
    media = (media_type or "").casefold()
    if media == "application/pdf" or suffix == ".pdf":
        return _PdfParser()
    if (
        media == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or suffix == ".docx"
    ):
        return _DocxParser()
    if media == "message/rfc822" or suffix in {".eml", ".msg"}:
        return _EmailParser()
    if (
        media.startswith("text/")
        or media in {"application/json", "application/xml"}
        or suffix
        in {
            ".txt",
            ".md",
            ".markdown",
            ".json",
            ".xml",
            ".csv",
            ".vtt",
            ".srt",
        }
    ):
        return _PlainTextParser()
    raise UnsupportedFormatError("No parser is registered for this file type")


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ParserError("The text file is not valid UTF-8") from error


def _normalize(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _paragraph_sections(text: str) -> tuple[ParsedSection, ...]:
    matches = list(re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|\Z)", text, re.DOTALL))
    return tuple(
        ParsedSection(match.group(), match.start(), match.end(), {"section": index + 1})
        for index, match in enumerate(matches)
    )


def _sections_from_parts(
    text: str, parts: list[str], locations: list[dict[str, object]]
) -> tuple[ParsedSection, ...]:
    sections: list[ParsedSection] = []
    cursor = 0
    for part, location in zip(parts, locations, strict=True):
        start = text.find(part, cursor)
        end = start + len(part)
        sections.append(ParsedSection(part, start, end, location))
        cursor = end
    return tuple(sections)


def _email_body(message: Any) -> str:
    if message.is_multipart():
        parts = [
            part.get_content()
            for part in message.walk()
            if part.get_content_type() == "text/plain" and not part.get_content_disposition()
        ]
        return "\n\n".join(value for value in parts if isinstance(value, str))
    value = message.get_content()
    return value if isinstance(value, str) else ""
