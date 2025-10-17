"""Tests for the search_youtube_videos MCP tool."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import ClassVar
from unittest import TestCase
from unittest.mock import MagicMock, patch


def _ensure_stub_dependencies() -> None:
    """Provide lightweight stand-ins for optional dependencies during tests."""
    if "youtube_transcript_api" not in sys.modules:
        stub = ModuleType("youtube_transcript_api")

        class _StubYouTubeTranscriptApi:
            def fetch(self, video_id: str) -> list[dict[str, object]]:
                return []

        stub.YouTubeTranscriptApi = _StubYouTubeTranscriptApi  # type: ignore[attr-defined]
        sys.modules["youtube_transcript_api"] = stub


def _load_mcp_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[1]
        / "mcp-server"
        / "content_mcp.py"
    )
    spec = importlib.util.spec_from_file_location("content_mcp", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load content_mcp module for testing")
    _ensure_stub_dependencies()
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SearchYouTubeToolTests(TestCase):
    content_mcp: ClassVar[ModuleType]

    @classmethod
    def setUpClass(cls) -> None:
        cls.content_mcp = _load_mcp_module()

    def test_search_requires_api_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                self.content_mcp.search_youtube_videos("test topic")

    def test_search_returns_formatted_results(self) -> None:
        payload = {
            "items": [
                {
                    "id": {"videoId": "abcdefghijk"},
                    "snippet": {"title": "First result"},
                },
                {
                    "id": {"videoId": "lmnopqrstuv"},
                    "snippet": {"title": "Second result"},
                },
            ]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(payload).encode("utf-8")
        mock_response.__enter__.return_value = mock_response

        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "dummy"}, clear=True):
            with patch.object(self.content_mcp.urlrequest, "urlopen", return_value=mock_response):
                result = self.content_mcp.search_youtube_videos("cats", max_results=5)

        self.assertIn("1. First result - https://www.youtube.com/watch?v=abcdefghijk", result)
        self.assertIn("2. Second result - https://www.youtube.com/watch?v=lmnopqrstuv", result)
        self.assertNotIn("3.", result)

    def test_search_handles_http_error(self) -> None:
        error_payload = {"error": {"message": "API quota exceeded"}}
        error_body = json.dumps(error_payload).encode("utf-8")

        class _FakeHTTPError(self.content_mcp.urlerror.HTTPError):
            def __init__(self) -> None:
                super().__init__(
                    url="https://example.com",
                    code=403,
                    msg="Forbidden",
                    hdrs=None,
                    fp=None,
                )
                self.fp = MagicMock()
                self.fp.read.return_value = error_body

        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "dummy"}, clear=True):
            with patch.object(
                self.content_mcp.urlrequest,
                "urlopen",
                side_effect=_FakeHTTPError(),
            ):
                with self.assertRaises(RuntimeError) as exc:
                    self.content_mcp.search_youtube_videos("quota", max_results=1)

        self.assertIn("API quota exceeded", str(exc.exception))
