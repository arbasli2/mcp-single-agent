from mcp.server.fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi
import re
import os

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
def fetch_intstructions(prompt_name: str) -> str:
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

if __name__ == "__main__":
    mcp.run(transport='stdio')