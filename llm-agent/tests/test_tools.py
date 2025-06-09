"""Tests for tools placeholder."""

import sys
from pathlib import Path
from unittest.mock import Mock

sys.path.append(str(Path(__file__).resolve().parents[2]))

from agent.tools import PaperDownloadTool


def test_placeholder():
    assert True


def test_paper_download_tool(monkeypatch, tmp_path):
    """Ensure PDFs are saved when the API returns results."""

    tool = PaperDownloadTool()

    # fake search response
    def fake_get(url, params=None, timeout=10):
        mock_resp = Mock()
        if "paper/search" in url:
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "data": [
                    {"title": "Paper One", "openAccessPdf": {"url": "http://pdf1"}},
                    {"title": "Paper Two", "openAccessPdf": {"url": "http://pdf2"}},
                ]
            }
            mock_resp.raise_for_status = lambda: None
            return mock_resp
        else:
            mock_resp.status_code = 200
            mock_resp.content = b"%PDF-1.4"
            mock_resp.raise_for_status = lambda: None
            mock_resp.ok = True
            return mock_resp

    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setenv("PAPERS_DIR", str(tmp_path))

    result = tool.run("test query")
    files = list(tmp_path.glob("*.pdf"))
    assert len(files) == 2
    assert result.startswith("Downloaded:")
