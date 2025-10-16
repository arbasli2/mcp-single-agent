"""Tests for the fetch_web_content MCP tool."""

from __future__ import annotations

import importlib.util
import socket
import sys
from pathlib import Path
from threading import Thread
from types import ModuleType
from typing import ClassVar
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import TestCase
from unittest.mock import MagicMock, patch


def _load_mcp_module() -> ModuleType:
    """Load the yt-mcp module directly from its path for test usage."""
    module_path = (
        Path(__file__).resolve().parents[1]
        / "mcp-server"
        / "yt-mcp.py"
    )
    spec = importlib.util.spec_from_file_location("yt_mcp", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load yt-mcp module for testing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FetchWebContentTests(TestCase):
    yt_mcp: ClassVar[ModuleType]

    @classmethod
    def setUpClass(cls) -> None:
        cls.yt_mcp = _load_mcp_module()

    def test_fetch_web_content_extracts_readable_text(self) -> None:
        html = (
            "<html><head><style>body{}</style></head>"
            "<body><h1>Title</h1><p>Paragraph 1</p><script>ignore()</script>"
            "<p>Paragraph 2</p></body></html>"
        ).encode("utf-8")

        mock_response = MagicMock()
        mock_response.read.return_value = html
        mock_response.headers.get_content_charset.return_value = "utf-8"
        mock_response.__enter__.return_value = mock_response

        with patch.object(self.yt_mcp.urlrequest, "urlopen", return_value=mock_response):
            result = self.yt_mcp.fetch_web_content("https://example.com/test")

        self.assertEqual(result, "Title\nParagraph 1\nParagraph 2")

    def test_fetch_web_content_truncates_long_output(self) -> None:
        long_text = "<p>" + ("data " * 2000) + "</p>"
        mock_response = MagicMock()
        mock_response.read.return_value = long_text.encode("utf-8")
        mock_response.headers.get_content_charset.return_value = "utf-8"
        mock_response.__enter__.return_value = mock_response

        with patch.object(self.yt_mcp.urlrequest, "urlopen", return_value=mock_response):
            result = self.yt_mcp.fetch_web_content("https://example.com/long", max_chars=100)

        self.assertTrue(result.endswith("...[truncated]"))
        self.assertLessEqual(len(result), 100 + len("\n\n...[truncated]"))

    def test_fetch_web_content_hits_real_http_endpoint(self) -> None:
        html_payload = (
            "<html><body><h2>Local Test</h2><p>Served from HTTP server.</p></body></html>"
        ).encode("utf-8")

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # type: ignore[override]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html_payload)

            def log_message(self, format, *args):
                return  # Suppress stdout noise during tests

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            host = server.server_address[0]
            port = server.server_port
            url = f"http://{host}:{port}/"
            result = self.yt_mcp.fetch_web_content(url)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.assertIn("Local Test", result)
        self.assertIn("Served from HTTP server.", result)

    def test_fetch_web_content_rejects_non_http_url(self) -> None:
        with self.assertRaises(ValueError):
            self.yt_mcp.fetch_web_content("ftp://example.com/resource")

    def test_fetch_web_content_surfaces_network_errors(self) -> None:
        with patch.object(
            self.yt_mcp.urlrequest,
            "urlopen",
            side_effect=self.yt_mcp.urlerror.URLError("timeout"),
        ):
            with self.assertRaises(Exception) as exc:
                self.yt_mcp.fetch_web_content("https://example.com/boom")

        self.assertIn("timeout", str(exc.exception))

    def test_fetch_web_content_reports_socket_timeout(self) -> None:
        with patch.object(
            self.yt_mcp.urlrequest,
            "urlopen",
            side_effect=self.yt_mcp.urlerror.URLError(socket.timeout("timed out")),
        ):
            with self.assertRaises(Exception) as exc:
                self.yt_mcp.fetch_web_content("https://example.com/slow", timeout_seconds=3)

        self.assertIn("Timed out after 3 seconds", str(exc.exception))
