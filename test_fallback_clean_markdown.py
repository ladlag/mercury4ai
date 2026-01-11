#!/usr/bin/env python3
"""
Focused test for the lightweight Stage 1 fallback cleaning.

This test installs a minimal dummy `crawl4ai` module so that the service
module can be imported without the real dependency being present.
"""

import sys
import types
import unittest


def _install_dummy_crawl4ai():
    if "crawl4ai" in sys.modules:
        return

    dummy = types.ModuleType("crawl4ai")

    class DummyCacheMode:
        BYPASS = "bypass"

    class DummyAsyncWebCrawler:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return False

    dummy.AsyncWebCrawler = DummyAsyncWebCrawler
    dummy.CacheMode = DummyCacheMode
    dummy.BrowserConfig = object

    extraction = types.ModuleType("crawl4ai.extraction_strategy")
    extraction.LLMExtractionStrategy = object

    sys.modules["crawl4ai"] = dummy
    sys.modules["crawl4ai.extraction_strategy"] = extraction


class FallbackCleaningTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _install_dummy_crawl4ai()

    def test_nav_and_footer_are_removed(self):
        from app.services.crawler_service import fallback_clean_markdown

        html = """
        <html>
            <body>
                <header>Header Links</header>
                <nav>Navigation</nav>
                <div class="content">
                    <p>Main body text</p>
                    <p>Second paragraph</p>
                </div>
                <footer>Footer notes</footer>
            </body>
        </html>
        """
        cleaned = fallback_clean_markdown(html)
        self.assertIn("Main body text", cleaned)
        self.assertIn("Second paragraph", cleaned)
        self.assertNotIn("Navigation", cleaned)
        self.assertNotIn("Header Links", cleaned)
        self.assertNotIn("Footer notes", cleaned)


if __name__ == "__main__":
    unittest.main()
