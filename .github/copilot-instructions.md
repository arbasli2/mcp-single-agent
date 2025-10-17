# Copilot Instructions

## Architecture Map
- Single-agent layout: `local_agent.py` and `openai_agent.py` both launch the `mcp-server/content_mcp.py` FastMCP instance defined in `MCP_ARCHITECTURE_DECISION.md`.
- System prompt lives in `mcp-server/prompts/system_instructions.md`; task-specific prompts in the same folder and fetched via MCP tools.
- `local_agent.py` drives conversations through `LocalContentAgent.process_message`, looping on tool calls until completions return prose; tool metadata is fetched live from the MCP server to keep schemas in sync.
- `openai_agent.py` provides an optional OpenAI Agents entry point; it mirrors the local flow but wraps execution in OpenAI tracing when `USE_OPENAI=true`.

## Tooling Details
- `search_youtube_videos` hits the YouTube Data API (set `YOUTUBE_API_KEY`) and returns numbered video titles + URLs; cap `max_results` to 10 and feed outputs into `fetch_video_transcript`.
- `fetch_video_transcript` enforces 11-char YouTube IDs and formats `[MM:SS] text`; agents should pass the raw URL and cite timestamps in outputs.
- `fetch_instructions` reads `prompts/{write_blog_post|write_social_post|write_video_chapters}.md`; never improvise those instructions—call the tool with the exact slug.
- `search_web` calls Google Programmable Search (set `GOOGLE_CSE_API_KEY` and `GOOGLE_CSE_ID`) and returns titles, URLs, and snippets to explore before `fetch_web_content`.
- `fetch_web_content` normalizes HTML via `_HTMLTextExtractor`, truncating to `max_chars`; handle timeouts and non-http schemes explicitly.
- `read_file` resolves real file paths, restricts extensions, and can be debugged with `READ_FILE_DEBUG=true`; optional deps `python-docx` and `pdfminer.six` are already listed in `pyproject.toml`.

## Runtime Workflow
- Install dependencies with `uv sync`; keep `.env` in the repo root to set `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_API_KEY`, optional `LOCAL_LLM_MODEL`, or `USE_OPENAI=true` with `OPENAI_API_KEY`.
- Run the local-first loop via `uv run local_agent.py`, or use `uv run openai_agent.py` when targeting OpenAI; `./run.sh` presents the same choices interactively.
- Set `YOUTUBE_API_KEY` in `.env` when you need YouTube search; transcript fetching works without it.
- Provide `GOOGLE_CSE_API_KEY` and `GOOGLE_CSE_ID` to enable `search_web`; without them the tool raises a helpful error.
- The MCP server runs under `uv run mcp-server/content_mcp.py` when launched directly; inspect `mcp-server/mcp-server.log` for rotating logs and tool diagnostics.
- Network retries and actionable error strings are handled inside `_create_chat_completion`; surface these messages to users instead of masking them.

## Testing Patterns
- Execute the suite with `uv run pytest`; tests live under `tests/` and rely on lightweight module loaders (see `_load_mcp_module` helpers).
- `tests/test_agent_multistep.py` fakes LLM completions to assert multi-step planning and retry behavior—follow this pattern when adding planner logic tests.
- Web fetching tests spin up a real `ThreadingHTTPServer`; prefer that approach over mocking when validating HTML extraction edge cases.
- When exercising `read_file`, reuse the temporary-file helpers and note the stub setup for `youtube_transcript_api` in `_ensure_stub_dependencies()`.

## Conventions
- Commands `exit` and `reset` are hard-coded control words in both entry points; preserve them in new UIs.
- Tool auto-selection skips `fetch_video_transcript` unless `_contains_youtube_url` matches; reuse that helper for YouTube detection.
- Respect the 6k character default when returning text from tools; truncate manually if new utilities return larger payloads.
- Keep new prompts co-located with the MCP server and register them through `fetch_instructions` rather than hard-coding copy in agents.
