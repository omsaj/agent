from pathlib import Path
from typing import Any, List
import yaml
from agent.tools import ArxivDownloadTool
from agent.tools import SmartResearchTool
from agent.tools import SciHubDownloadTool
from agent.tools import BulkURLResearchTool
from agent.tools import ScholarResearchTool
from agent.tools import ScholarSearchTool
from agent.tools import (
    EchoTool,
    PaperDownloadTool,
    PDFExtractTool,
    OllamaChatTool,
    ResearchAssistantTool,
    
)
from dotenv import load_dotenv
load_dotenv()
class LocalAgent:
    """Simple local LLM agent."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        if config_path is None:
            config_path = Path(__file__).resolve().parents[1] / "config" / "config.yaml"
        else:
            config_path = Path(config_path)

        with open(config_path, "r", encoding="utf-8") as f:
            self.config: dict[str, Any] = yaml.safe_load(f)

        self.memory: List[str] = []

        self.tools = {
            "echo": EchoTool(),
            "download_papers": PaperDownloadTool(),
            "pdf_extract": PDFExtractTool(),
            "ollama_chat": OllamaChatTool(),
            "research_assistant": ResearchAssistantTool(),
            "arxiv_download": ArxivDownloadTool(),
            "smart_research": SmartResearchTool(),
            "scihub_download": SciHubDownloadTool(),
            "scholar_search": ScholarSearchTool(),
            "bulk_research_from_links": BulkURLResearchTool(),
            "scholar_research": ScholarResearchTool(),
        }

    def process_input(self, text: str) -> str:
        self.memory.append(text)
        return "Processed: " + text

    def run_tool(self, name: str, input: str) -> str:
        tool = self.tools.get(name)
        if tool:
            return tool.run(input)
        return "Tool not found"
