from __future__ import annotations

from src.lead_intelligence.resource_filter import (
    classify_content_type,
    classify_resource_url,
    extract_url_extension,
)


def test_html_path_with_no_extension_is_crawlable_html() -> None:
    """Extensionless paths should be treated as HTML-like pages."""

    classification = classify_resource_url("https://example.de/kontakt")

    assert classification.category == "html"
    assert classification.extension == ""
    assert classification.crawlable_html is True
    assert classification.document_link is False
    assert classification.excluded_reason is None


def test_html_extension_is_crawlable_html() -> None:
    """Explicit HTML extensions should be crawlable."""

    classification = classify_resource_url("https://example.de/index.html")

    assert classification.category == "html"
    assert classification.extension == ".html"
    assert classification.crawlable_html is True


def test_pdf_document_is_document_link() -> None:
    """PDF links should be recorded as documents, not crawled as pages."""

    classification = classify_resource_url("https://example.de/report.pdf")

    assert classification.category == "document"
    assert classification.document_link is True
    assert classification.crawlable_html is False
    assert classification.excluded_reason == "document resource (.pdf)"


def test_word_and_excel_documents_are_document_links() -> None:
    """Office documents should be recognised."""

    assert classify_resource_url("https://example.de/spec.docx").category == (
        "document"
    )
    assert classify_resource_url("https://example.de/list.xlsx").category == (
        "document"
    )


def test_css_is_asset() -> None:
    """CSS files should be skipped as assets."""

    assert classify_resource_url("https://example.de/app.css").category == (
        "asset"
    )


def test_javascript_is_asset() -> None:
    """JavaScript files should be skipped as assets."""

    assert classify_resource_url("https://example.de/app.js").category == (
        "asset"
    )


def test_image_is_asset() -> None:
    """Images should be skipped as assets."""

    assert classify_resource_url("https://example.de/logo.png").category == (
        "asset"
    )


def test_archive_is_archive() -> None:
    """Archives should be skipped."""

    assert classify_resource_url("https://example.de/files.zip").category == (
        "archive"
    )


def test_query_parameters_do_not_affect_extension() -> None:
    """Extension detection should use only the URL path."""

    assert (
        extract_url_extension("https://example.de/report.pdf?download=html")
        == ".pdf"
    )


def test_fragment_does_not_affect_extension() -> None:
    """Fragments should be ignored for extension detection."""

    assert (
        extract_url_extension("https://example.de/style.css#content")
        == ".css"
    )


def test_content_type_parameters_are_ignored() -> None:
    """Content-Type classification should ignore parameters."""

    assert classify_content_type("text/html; charset=utf-8") == "html"


def test_application_pdf_content_type_becomes_document() -> None:
    """PDF content should be classified as a document."""

    assert classify_content_type("application/pdf") == "document"


def test_image_png_content_type_becomes_asset() -> None:
    """Images should be classified as assets."""

    assert classify_content_type("image/png") == "asset"


def test_unknown_content_type_is_unknown() -> None:
    """Missing or unsupported content types should be unknown."""

    assert classify_content_type(None) == "unknown"
    assert classify_content_type("application/x-custom") == "unknown"
