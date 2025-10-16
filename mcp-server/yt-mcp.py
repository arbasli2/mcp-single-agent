from mcp.server.fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi
import re
import os
import socket
from html.parser import HTMLParser
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

# Suppress MCP INFO logs to reduce console output
import logging
logging.getLogger("mcp").setLevel(logging.WARNING)

# Create an MCP server
mcp = FastMCP("yt-mcp")

# Create prompt
@mcp.prompt()
def system_prompt() -> str:
    """Instructions for YouTube video agent"""
    script_dir = os.path.dirname(__file__)
    prompt_path = os.path.join(script_dir, "prompts", "system_instructions.md")
    with open(prompt_path, "r") as file:
        return file.read()

# Create tool
@mcp.tool()
def fetch_video_transcript(url: str) -> str:
    """
    Extract transcript with timestamps from a YouTube video URL and format it for analysis.
    
    Use this tool when:
    - User provides a YouTube URL and wants video content analysis
    - User asks to summarize, analyze, or process a YouTube video
    - User wants to create content based on a YouTube video
    
    Args:
        url (str): YouTube video URL (youtube.com or youtu.be format)
        
    Returns:
        str: Formatted transcript with timestamps, where each entry is on a new line
             in the format: "[MM:SS] Text"
    """
    # Extract video ID from URL
    video_id_pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    video_id_match = re.search(video_id_pattern, url)
    
    if not video_id_match:
        raise ValueError("Invalid YouTube URL")
    
    video_id = video_id_match.group(1)
    
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id)
        
        # Format each entry with timestamp and text
        formatted_entries = []
        for entry in transcript:
            # Convert seconds to MM:SS format
            minutes = int(entry.start // 60)
            seconds = int(entry.start % 60)
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
            
            formatted_entry = f"{timestamp} {entry.text}"
            formatted_entries.append(formatted_entry)
        
        # Join all entries with newlines
        return "\n".join(formatted_entries)
    
    except Exception as e:
        raise Exception(f"Error fetching transcript: {str(e)}")

@mcp.tool()
def fetch_instructions(prompt_name: str) -> str:
    """
    Fetch specialized writing instructions and guidelines for creating different types of content.

    Use this tool when user wants to:
    - Write a blog post (use prompt_name: "write_blog_post")
    - Create social media content (use prompt_name: "write_social_post") 
    - Generate video chapter timestamps (use prompt_name: "write_video_chapters")

    Args:
        prompt_name (str): Type of instructions to fetch
        Available options: 
            - "write_blog_post": Guidelines for writing blog posts
            - "write_social_post": Guidelines for social media content
            - "write_video_chapters": Guidelines for creating video chapter timestamps

    Returns:
        str: Detailed instructions and guidelines for the requested content type
    """
    script_dir = os.path.dirname(__file__)
    prompt_path = os.path.join(script_dir, "prompts", f"{prompt_name}.md")
    with open(prompt_path, "r") as f:
        return f.read()


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._tokens: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        elif tag in {"p", "div", "section", "article", "li", "br", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._tokens.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag in {"p", "div", "section", "article", "li"}:
            self._tokens.append("\n")

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        stripped = data.strip()
        if stripped:
            self._tokens.append(stripped)

    def get_text(self) -> str:
        lines: list[str] = []
        current: list[str] = []
        for token in self._tokens:
            if token == "\n":
                if current:
                    lines.append(" ".join(current).strip())
                    current = []
            else:
                current.append(token)
        if current:
            lines.append(" ".join(current).strip())
        return "\n".join(line for line in lines if line)


@mcp.tool()
def fetch_web_content(url: str, max_chars: int = 6000, timeout_seconds: int = 20) -> str:
    """Fetch readable text content from a public webpage.

    Args:
        url (str): HTTP or HTTPS URL to fetch.
        max_chars (int): Optional upper bound on returned characters to prevent huge responses.
        timeout_seconds (int): Maximum seconds to wait for the HTTP request.

    Returns:
        str: Extracted body text, truncated to ``max_chars`` characters when needed.
    """
    parsed = urlparse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http and https URLs are supported")

    timeout = max(1, min(int(timeout_seconds), 120))
    req = urlrequest.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; yt-mcp-agent/1.0)"})
    try:
        with urlrequest.urlopen(req, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            html_bytes = response.read()
    except urlerror.URLError as exc:
        reason = exc.reason
        if isinstance(reason, socket.timeout):
            raise Exception(f"Timed out after {timeout} seconds while fetching the URL")
        raise Exception(f"Error fetching URL: {reason}")

    try:
        html_text = html_bytes.decode(charset, errors="replace")
    except LookupError:
        html_text = html_bytes.decode("utf-8", errors="replace")

    extractor = _HTMLTextExtractor()
    extractor.feed(html_text)
    text = extractor.get_text()

    if not text:
        return "No readable text content found at the provided URL."

    trimmed = text[:max_chars]
    if len(text) > max_chars:
        trimmed += "\n\n...[truncated]"
    return trimmed

if __name__ == "__main__":
    mcp.run(transport='stdio')