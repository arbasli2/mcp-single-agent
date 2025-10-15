# MCP Server Architecture Decision

## Current Approach

The project now focuses on a single YouTube agent that owns its MCP server and prompts:

```
youtube-agent/
├── openai_agent.py  # OpenAI Responses API entry point
├── local_agent.py   # Local LLM entry point
└── mcp-server/
    ├── yt-mcp.py
    └── prompts/
        ├── system_instructions.md
        ├── write_blog_post.md
        ├── write_social_post.md
        └── write_video_chapters.md
```

## Guiding Principles

1. **Domain Encapsulation** – Each agent owns the MCP tools and prompts that match its problem space.
2. **Independence** – Agents can be developed, deployed, and versioned separately.
3. **Failure Isolation** – Problems in one agent’s MCP server stay contained.
4. **Security** – Tool access is scoped to the agent that needs it.
5. **Resource Tuning** – Hardware can be tailored per agent (GPU, CPU, memory, network).

## Adding Another Standalone Agent

When creating a new domain agent (web, code, etc.):

1. Scaffold a copy of the YouTube agent layout under a new folder.
2. Build a domain-specific MCP server with the minimal tool surface.
3. Author clear system instructions and task prompts.
4. Provide a CLI entry point similar to `openai_agent.py` / `local_agent.py`.
5. Keep each agent self-contained; agents do not orchestrate one another.

## Summary

This architecture keeps the codebase simple while leaving room to spin up additional single-purpose agents when needed. Multi-agent orchestration has been deprecated in favor of independent, focused agents.