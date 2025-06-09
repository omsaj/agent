"""Tool definitions for the local agent."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Tool(ABC):
    """Base interface for agent tools."""

    name: str
    description: str

    @abstractmethod
    def run(self, input: str) -> str:
        """Run the tool using ``input`` and return its result."""
        raise NotImplementedError


class EchoTool(Tool):
    """Tool that simply echoes the provided input."""

    name = "echo"
    description = "Return the input text prefixed with 'Echo:'"

    def run(self, input: str) -> str:
        """Return ``input`` wrapped in an echo string."""
        return f"Echo: {input}"


class PaperDownloadTool(Tool):
    """Search Semantic Scholar and download a few PDFs for later parsing."""

    name = "download_papers"
    description = (
        "Search Semantic Scholar for papers matching a query and save up to "
        "three PDFs locally."
    )

    def run(self, input: str) -> str:
        import os
        from pathlib import Path
        import requests

        query = input.strip()
        if not query:
            return "No query provided"

        search_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": 3,
            "fields": "title,openAccessPdf",
        }

        try:
            resp = requests.get(search_url, params=params, timeout=10)
            resp.raise_for_status()
        except Exception as exc:
            return f"Search failed: {exc}"

        data = resp.json()
        papers = data.get("data", [])
        if not papers:
            return "No results found"

        save_dir = Path(
            os.getenv("PAPERS_DIR", Path(__file__).resolve().parents[1] / "papers")
        )
        save_dir.mkdir(parents=True, exist_ok=True)

        downloaded: list[str] = []
        for paper in papers:
            pdf_url = paper.get("openAccessPdf", {}).get("url")
            title = paper.get("title", "paper")
            if not pdf_url:
                continue
            try:
                pdf_resp = requests.get(pdf_url, timeout=10)
                pdf_resp.raise_for_status()
            except Exception:
                continue

            name = title[:50].replace("/", "_").replace(" ", "_") + ".pdf"
            path = save_dir / name
            with open(path, "wb") as f:
                f.write(pdf_resp.content)
            downloaded.append(str(path))

        if not downloaded:
            return "No PDFs downloaded"

        return "Downloaded: " + ", ".join(downloaded)


class PDFExtractTool(Tool):
    """Extract all text content from a PDF file."""

    name = "pdf_extract"
    description = "Extract and return text from a PDF given its file path"

    def run(self, input: str) -> str:
        from pathlib import Path
        import fitz  # PyMuPDF

        path = Path(input.strip())
        if not path.is_file():
            return "File not found"

        try:
            doc = fitz.open(path)
        except Exception as exc:
            return f"Failed to open PDF: {exc}"

        texts: list[str] = []
        for page in doc:
            texts.append(page.get_text())
        doc.close()

        return "\n".join(texts)
