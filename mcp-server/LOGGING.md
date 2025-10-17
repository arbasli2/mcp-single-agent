# MCP Server Logging Configuration

The MCP content server has been configured to log all activities to a file instead of stderr for better monitoring and debugging.

## Log File Location
- **File**: `mcp-server/mcp-server.log`
- **Format**: `YYYY-MM-DD HH:MM:SS - logger_name - LEVEL - message`

## Log Rotation
- **Max file size**: 10MB per log file
- **Backup files**: 5 rotating backup files are kept
- **Files**: `mcp-server.log`, `mcp-server.log.1`, `mcp-server.log.2`, etc.

## Log Levels
- **INFO**: Tool function calls, successful operations, server startup
- **WARNING**: Non-critical issues (no content extracted, etc.)
- **ERROR**: Errors and exceptions with full tracebacks

## Logged Events
- Server startup and shutdown
- Tool function calls (fetch_video_transcript, read_file, fetch_web_content, fetch_instructions)
- Successful operations with metrics (file sizes, character counts, etc.)
- Errors and exceptions with context
- Debug information (when READ_FILE_DEBUG=true environment variable is set)

## Examples
```
2025-10-17 12:45:02 - root - INFO - Starting MCP content server...
2025-10-17 12:45:15 - root - INFO - Reading file: /path/to/document.pdf (max_chars: 6000)
2025-10-17 12:45:16 - root - INFO - Successfully read file /path/to/document.pdf (1250 chars)
2025-10-17 12:45:20 - root - INFO - Fetching web content from: https://example.com (max_chars: 6000, timeout: 20s)
2025-10-17 12:45:22 - root - ERROR - URL error for https://example.com: HTTP Error 404: Not Found
```

## Debug Mode
Set the environment variable `READ_FILE_DEBUG=true` to enable detailed debug logging for file operations:
```bash
READ_FILE_DEBUG=true uv run python mcp-server/content_mcp.py
```