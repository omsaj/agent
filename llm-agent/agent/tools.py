from abc import ABC, abstractmethod
from cmath import e
import requests
import os
import fitz
import feedparser
import re
from bs4 import BeautifulSoup
from serpapi import GoogleSearch


class Tool(ABC):
    name: str
    description: str

    @abstractmethod
    def run(self, input: str) -> str:
        ...

class EchoTool(Tool):
    name = "echo"
    description = "Echoes the input string"

    def run(self, input: str) -> str:
        return f"Echo: {input}"

class PaperDownloadTool(Tool):
    name = "download_papers"
    description = "Download papers from Semantic Scholar for a given query"

    def run(self, input: str) -> str:
        try:
            os.makedirs("papers", exist_ok=True)
            resp = requests.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={"query": input, "limit": 10, "fields": "title,url,openAccessPdf"},
                timeout=30
            )
            papers = resp.json().get("data", [])
            print(f"[DEBUG] Received {len(papers)} papers from Semantic Scholar")

            results = []
            for i, paper in enumerate(papers):
                print(f"[DEBUG] Paper {i+1} title: {paper.get('title')}")
                pdf_url = paper.get("openAccessPdf", {}).get("url")
                if not pdf_url:
                    print(f"[DEBUG] No open-access PDF for: {paper.get('title')}")
                    continue

                if pdf_url:
                    # Skip DOI or known HTML wrappers
                    if "doi.org" in pdf_url or "mdpi.com" in pdf_url or "springer.com" in pdf_url:
                        print(f"[DEBUG] Skipping DOI/wrapped link: {pdf_url}")
                        continue

                    try:
                        print(f"[DEBUG] Downloading from: {pdf_url}")
                        response = requests.get(pdf_url, timeout=30)
                        content_type = response.headers.get("Content-Type", "")
                        if "application/pdf" not in content_type:
                            print(f"[DEBUG] Skipped non-PDF response from {pdf_url} (Content-Type: {content_type})")
                            continue

                        filename = f"papers/paper_{i+1}.pdf"
                        with open(filename, "wb") as f:
                            f.write(response.content)
                        results.append(f"Downloaded: {filename}")
                    except Exception as e:
                        print(f"[DEBUG] Failed to download {pdf_url}: {e}")


                    filename = f"papers/paper_{i+1}.pdf"
                    with open(filename, "wb") as f:
                        f.write(response.content)
                    results.append(f"Downloaded: {filename}")
                else:
                    print(f"[DEBUG] Skipping non-direct PDF URL: {pdf_url}")
            return "\n".join(results) or "No open-access PDFs found"
        except Exception as e:
            return f"Error downloading papers: {e}"



class PDFExtractTool(Tool):
    name = "pdf_extract"
    description = "Extract text from a PDF file using PyMuPDF"

    def run(self, input: str) -> str:
        try:
            doc = fitz.open(input)
            text = "\n".join([page.get_text() for page in doc])
            doc.close()
            return text or "[No text extracted]"
        except Exception as e:
            return f"Failed to extract text: {e}"

class OllamaChatTool(Tool):
    name = "ollama_chat"
    description = "Chat with a local LLM via Ollama"

    def run(self, input: str) -> str:
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.1:8b-instruct-q4_K_M",
                    "prompt": input,
                    "stream": False
                },
                timeout=30
            )
            return response.json().get("response", "[No response]")
        except Exception as e:
            return f"Ollama error: {e}"

class ResearchAssistantTool(Tool):
    name = "research_assistant"
    description = "Search, download, extract, and summarize papers using local LLM"

    def run(self, input: str) -> str:
        downloader = PaperDownloadTool()
        extractor = PDFExtractTool()
        chat = OllamaChatTool()

        download_result = downloader.run(input)
        lines = download_result.splitlines()
        summaries = []

        for line in lines:
            if line.startswith("Downloaded:"):
                path = line.split("Downloaded:")[1].strip()
                text = extractor.run(path)
                if text and "Failed" not in text:
                    summary = chat.run(f"Summarize this paper:\n{text[:4000]}")
                    summaries.append(f"Summary of {path}:\n{summary}")

        return "\n\n".join(summaries) or "No summaries generated"

class ArxivDownloadTool(Tool):
    name = "arxiv_download"
    description = "Download top 10 full-text papers from arXiv for a given query"

    def run(self, input: str) -> str:
        try:
            os.makedirs("papers", exist_ok=True)
            print(f"[DEBUG] Searching arXiv for: {input}")

            # Use arXiv RSS feed as search (limited but effective)
            query = input.replace(" ", "+")
            feed_url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=10"

            feed = feedparser.parse(feed_url)
            if not feed.entries:
                return "No results found on arXiv."

            results = []
            for i, entry in enumerate(feed.entries):
                title = entry.title
                pdf_link = next((link.href for link in entry.links if link.type == "application/pdf"), None)
                if not pdf_link:
                    print(f"[DEBUG] No PDF for: {title}")
                    continue

                print(f"[DEBUG] Downloading: {title}")
                response = requests.get(pdf_link, timeout=20)
                filename = f"papers/arxiv_{i+1}.pdf"
                with open(filename, "wb") as f:
                    f.write(response.content)
                results.append(f"Downloaded: {filename} – {title}")

            return "\n".join(results) or "No valid PDFs found."
        except Exception as e:
            return f"Error querying arXiv: {e}"
class SmartResearchTool(Tool):
    name = "smart_research"
    description = "End-to-end research tool that plans, refines, and fetches papers using an LLM loop"

    def run(self, input: str) -> str:
        planner = OllamaChatTool()
        downloader = ArxivDownloadTool()
        extractor = PDFExtractTool()
        summarizer = OllamaChatTool()

        keyword_prompt = (
            f"Given this research outline:\n\n{input}\n\n"
            f"Generate 3 simple, short search queries (no quotes, no boolean operators) "
            f"for searching arXiv.org. Just return one query per line."
        )

        keywords = planner.run(keyword_prompt)
        raw_lines = keywords.strip().split("\n")
        cleaned_keywords = []

        for line in raw_lines:
            # Remove bullets like "1." or "2." and surrounding quotes
            term = re.sub(r'^\d+\.\s*', '', line)
            term = term.replace('"', '')
            term = re.sub(r'AND|OR|\(|\)', '', term)
            term = term.strip()
            if term:
                cleaned_keywords.append(term)

            print(f"[DEBUG] Cleaned keywords: {cleaned_keywords}")
            print(f"[DEBUG] Initial keywords:\n{keywords}")

        summaries = []
        for kw in keywords.strip().split("\n")[:3]:
            print(f"[DEBUG] Searching for: {kw}")
            result = downloader.run(kw)
            print(f"[DEBUG] Download result:\n{result}")
            lines = result.splitlines()
            for line in lines:
                if line.startswith("Downloaded:"):
                    path = line.split("Downloaded:")[1].strip()
                    text = extractor.run(path)
                    if text and "Failed" not in text:
                        summary = summarizer.run(f"Summarize this paper:\n{text[:4000]}")
                        summaries.append(f"Summary of {path}:\n{summary}")

        joined = "\n\n".join(summaries)
        refinement_prompt = f"Based on these summaries, suggest better search terms to find more relevant papers:\n\n{joined}"
        new_keywords = planner.run(refinement_prompt)

        return f"Initial Summaries:\n{joined}\n\nSuggested Next Search Terms:\n{new_keywords}"
    

class SciHubDownloadTool(Tool):
    name = "scihub_download"
    description = "Download a paper PDF from Sci-Hub using DOI or title (for testing only)"

    def run(self, input: str) -> str:
        try:
            os.makedirs("papers", exist_ok=True)

            # Use one of the active mirrors
            base_url = "https://sci-hub.st"  # try .st or .ru if blocked

            # 🛠 Add a real browser user-agent to bypass bot filters
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/113.0.0.0 Safari/537.36"
                )
            }

            print(f"[DEBUG] Querying Sci-Hub: {base_url}/{input}")
            response = requests.get(f"{base_url}/{input}", headers=headers, timeout=20)
            if response.status_code != 200:
                return f"Failed to load Sci-Hub page: {response.status_code}"

            soup = BeautifulSoup(response.content, "html.parser")
            iframe = soup.find("iframe")
            if not iframe or not iframe.get("src"):
                return "PDF not found on Sci-Hub page."

            pdf_url = iframe["src"]
            if pdf_url.startswith("//"):
                pdf_url = "https:" + pdf_url
            elif pdf_url.startswith("/"):
                pdf_url = base_url + pdf_url

            print(f"[DEBUG] Downloading PDF from: {pdf_url}")
            pdf_data = requests.get(pdf_url, headers=headers, timeout=20).content
            filename = "papers/scihub_test.pdf"
            with open(filename, "wb") as f:
                f.write(pdf_data)

            return f"Downloaded: {filename}"
        except Exception as e:
            return f"Error downloading from Sci-Hub: {e}"
    from serpapi import GoogleSearch

class ScholarSearchTool(Tool):
    name = "scholar_search"
    description = "Search Google Scholar using SerpAPI and return top 3 results with titles and links"

    def run(self, input: str) -> str:
        try:
            api_key = os.getenv("SERPAPI_API_KEY")
            if not api_key:
                return "Error: SERPAPI_API_KEY not set in environment."

            params = {
                "engine": "google_scholar",
                "q": input,
                "num": 3,
                "api_key": api_key
            }

            search = GoogleSearch(params)
            results = search.get_dict()
            entries = results.get("organic_results", [])

            if not entries:
                return "No results found."

            output = []
            for i, entry in enumerate(entries, start=1):
                if not entry:
                    continue

                title = entry.get("title") or "[No title]"
                link = entry.get("link") or "[No link]"
                snippet = entry.get("snippet") if "snippet" in entry else "[No snippet]"

                # Sci-Hub fallback (optional)
                from agent.tools import SciHubDownloadTool
                scihub = SciHubDownloadTool()
                dl_result = scihub.run(link)

                output.append(f"{i}. {title}\n{link}\n{snippet}\n{dl_result}\n")

            return "\n".join(output)
        except Exception as e:
            return f"Error using SerpAPI: {e}"

class BulkURLResearchTool(Tool):
    name = "bulk_research_from_links"
    description = "Download, extract, and summarize PDFs from a list of links in a .txt file"

    def run(self, input: str) -> str:
        try:
            if not os.path.isfile(input):
                return f"File not found: {input}"

            os.makedirs("papers", exist_ok=True)
            extractor = PDFExtractTool()
            summarizer = OllamaChatTool()

            with open(input, "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip()]

            if not urls:
                return "No URLs found in the file."

            summaries = []
            for i, url in enumerate(urls, start=1):
                print(f"[DEBUG] Processing URL {i}: {url}")

                if not url.lower().endswith(".pdf"):
                    print(f"[WARN] Skipping non-PDF link: {url}")
                    continue

                try:
                    response = requests.get(url, timeout=20)
                    content_type = response.headers.get("Content-Type", "")
                    if "application/pdf" not in content_type:
                        print(f"[WARN] Skipping invalid PDF: {url} (Content-Type: {content_type})")
                        continue

                    filename = f"papers/bulk_{i}.pdf"
                    with open(filename, "wb") as f:
                        f.write(response.content)
                    print(f"[INFO] Downloaded: {filename}")

                    text = extractor.run(filename)
                    if text and "Failed" not in text:
                        summary = summarizer.run(f"Summarize this paper:\n{text[:4000]}")
                        summaries.append(f"### Summary of {filename}\n{summary}\n")
                except Exception as e:
                    print(f"[ERROR] Failed to process {url}: {e}")

            return "\n".join(summaries) or "No valid PDFs processed."
        except Exception as e:
            return f"Error processing bulk research: {e}"
class ScholarResearchTool(Tool):
    name = "scholar_research"
    description = "Search Google Scholar, download and summarize open PDFs based on a user outline"

    def run(self, input: str) -> str:
        try:
            from serpapi import GoogleSearch

            # Step 1: Let LLM generate search terms
            planner = OllamaChatTool()
            keyword_prompt = (
                f"Based on this research topic:\n\n{input}\n\n"
                f"Generate 2-3 search terms suitable for Google Scholar. "
                f"Return just the terms, one per line, no extra text."
            )
            keywords = planner.run(keyword_prompt).strip().splitlines()
            print(f"[DEBUG] LLM-generated search terms: {keywords}")

            api_key = os.getenv("SERPAPI_API_KEY")
            if not api_key:
                return "Error: SERPAPI_API_KEY not set."

            extractor = PDFExtractTool()
            summarizer = OllamaChatTool()
            summaries = []

            for keyword in keywords[:3]:
                print(f"[DEBUG] Searching for: {keyword}")
                params = {
                    "engine": "google_scholar",
                    "q": keyword,
                    "num": 5,
                    "api_key": api_key
                }

                search = GoogleSearch(params)
                results = search.get_dict()
                entries = results.get("organic_results", [])

                for i, entry in enumerate(entries, start=1):
                    title = entry.get("title") or "[No title]"
                    link = entry.get("link", "")
                    
                    if not link:
                        continue

                    
                    print(f"[DEBUG] Attempting download: {link}")
                    response = requests.get(link, timeout=20)
                    content_type = response.headers.get("Content-Type", "")
                    if "application/pdf" not in content_type:
                        print(f"[WARN] Skipping non-PDF content: {link} ({content_type})")
                        continue


                    try:
                        print(f"[DEBUG] Downloading: {title}")
                        response = requests.get(link, timeout=20)
                        content_type = response.headers.get("Content-Type", "")
                        if "application/pdf" not in content_type:
                            print(f"[WARN] Skipping non-PDF content: {link} ({content_type})")
                            continue

                        filename = f"papers/scholar_{i}.pdf"
                        with open(filename, "wb") as f:
                            f.write(response.content)

                        text = extractor.run(filename)
                        if text and "Failed" not in text:
                            summary = summarizer.run(f"Summarize this paper:\n{text[:4000]}")
                            summaries.append(f"### {title}\n{summary}\n")
                    except Exception as e:
                        print(f"[ERROR] Failed to download/summarize: {e}")

            return "\n\n".join(summaries) or "No valid summaries generated."
        except Exception as e:
            return f"Error in scholar_research: {e}"