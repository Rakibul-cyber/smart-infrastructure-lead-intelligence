from __future__ import annotations

import contextlib
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from src.lead_intelligence.dynamic_scraper import (
    DynamicPageOptions,
    scrape_dynamic_page,
)


FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures"
FIXTURE_FILENAME = "dynamic_page.html"


class QuietFixtureHandler(SimpleHTTPRequestHandler):
    """Serve local fixtures without request logging noise."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            directory=str(FIXTURE_DIRECTORY),
            **kwargs,
        )

    def log_message(self, format: str, *args) -> None:
        return None


def main() -> None:
    """Render the local dynamic fixture and print extracted counts."""

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        QuietFixtureHandler,
    )
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()

    try:
        host, port = server.server_address
        url = f"http://{host}:{port}/{FIXTURE_FILENAME}"
        result = scrape_dynamic_page(
            url,
            options=DynamicPageOptions(
                wait_for_selector="#dynamic-content",
                wait_after_load_seconds=0.1,
            ),
        )
        page = result.scraped_page
        preview = page.visible_text[:120]

        print(f"Final URL: {result.final_url}")
        print(f"Title: {result.page_title}")
        print(f"Main heading: {page.main_heading}")
        print(f"Visible-text preview: {preview}")
        print(f"Email count: {len(page.emails)}")
        print(f"Phone count: {len(page.phone_numbers)}")
        print(f"Internal-link count: {len(page.internal_links)}")

    finally:
        server.shutdown()
        server.server_close()

        with contextlib.suppress(RuntimeError):
            thread.join(timeout=2)


if __name__ == "__main__":
    main()
