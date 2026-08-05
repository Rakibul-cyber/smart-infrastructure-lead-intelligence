from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse


@dataclass(frozen=True)
class ResourceClassification:
    """Transparent crawl classification for a URL-like resource."""

    url: str
    category: str
    extension: str
    crawlable_html: bool
    document_link: bool
    excluded_reason: str | None


HTML_EXTENSIONS = {
    "",
    ".html",
    ".htm",
    ".php",
    ".asp",
    ".aspx",
    ".jsp",
}

DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".odt",
    ".ods",
    ".rtf",
    ".txt",
    ".csv",
}

ASSET_EXTENSIONS = {
    ".css",
    ".js",
    ".json",
    ".xml",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".mp3",
    ".mp4",
    ".webm",
    ".avi",
    ".mov",
}

ARCHIVE_EXTENSIONS = {
    ".zip",
    ".tar",
    ".gz",
    ".rar",
    ".7z",
}

DOCUMENT_CONTENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/rtf",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.spreadsheet",
    "text/csv",
    "text/plain",
}

ASSET_CONTENT_TYPES = {
    "text/css",
    "application/javascript",
    "text/javascript",
    "application/json",
    "application/xml",
    "text/xml",
}

BINARY_HINT_EXTENSIONS = (
    ".bin",
    ".exe",
    ".dmg",
    ".iso",
)


def extract_url_extension(url: str) -> str:
    """
    Return the lowercase path extension for a URL.

    Query parameters and fragments are ignored. An empty string means either no
    extension or no meaningful path extension.
    """

    try:
        path = unquote(urlparse(url).path)
    except ValueError:
        return ""

    suffix = PurePosixPath(path).suffix.casefold()

    if not suffix or suffix == ".":
        return ""

    return suffix


def classify_resource_url(url: str) -> ResourceClassification:
    """Classify a URL by extension before adding it to the crawl queue."""

    extension = extract_url_extension(url)

    if extension in HTML_EXTENSIONS:
        return ResourceClassification(
            url=url,
            category="html",
            extension=extension,
            crawlable_html=True,
            document_link=False,
            excluded_reason=None,
        )

    if extension in DOCUMENT_EXTENSIONS:
        return ResourceClassification(
            url=url,
            category="document",
            extension=extension,
            crawlable_html=False,
            document_link=True,
            excluded_reason=f"document resource ({extension})",
        )

    if extension in ASSET_EXTENSIONS:
        return ResourceClassification(
            url=url,
            category="asset",
            extension=extension,
            crawlable_html=False,
            document_link=False,
            excluded_reason=f"asset resource ({extension})",
        )

    if extension in ARCHIVE_EXTENSIONS:
        return ResourceClassification(
            url=url,
            category="archive",
            extension=extension,
            crawlable_html=False,
            document_link=False,
            excluded_reason=f"archive resource ({extension})",
        )

    crawlable_html = not extension.endswith(BINARY_HINT_EXTENSIONS)

    return ResourceClassification(
        url=url,
        category="unknown",
        extension=extension,
        crawlable_html=crawlable_html,
        document_link=False,
        excluded_reason=None
        if crawlable_html
        else f"binary-looking resource ({extension})",
    )


def classify_content_type(
    content_type: str | None,
) -> str:
    """Classify a response Content-Type without considering parameters."""

    if content_type is None:
        return "unknown"

    media_type = content_type.split(";", 1)[0].strip().casefold()

    if media_type in {"text/html", "application/xhtml+xml"}:
        return "html"

    if media_type in DOCUMENT_CONTENT_TYPES:
        return "document"

    if media_type in ASSET_CONTENT_TYPES:
        return "asset"

    if (
        media_type.startswith("image/")
        or media_type.startswith("audio/")
        or media_type.startswith("video/")
        or media_type.startswith("font/")
    ):
        return "asset"

    return "unknown"
