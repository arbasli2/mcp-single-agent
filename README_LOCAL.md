# yt-mcp-agent
A  agent built using a custom MCP server that works with both OpenAI's API and local LLMs. It can extract video transcripts and fetch specialized instructions for writing blog posts, video chapters, and social posts. It also can fetch web pages.

## 🆕 Local LLM Support
This project now includes **`local_agent.py`** - a simplified version that works with local LLMs without requiring OpenAI's proprietary Agents SDK.

**Key differences:**
- ✅ **Works with local LLMs** (LM Studio, Ollama, etc.)
- ✅ **No dependency on OpenAI Agents SDK**
- ✅ **Same core functionality** (YouTube transcripts, content generation)
- ❌ **No advanced tracing** (OpenAI-specific feature)
- ❌ **No agent handoffs** (simplified single-agent approach)

Resources:
- [Talk recording](https://youtu.be/w-Ml3NivoFo)
- [Slides](https://drive.google.com/file/d/1id7V9nrNetW72k6vERS6oTy0bW0wEloo/view?usp=sharing)

>This example is a prelude to [Cohort 7](https://github.com/ShawhinT/AI-Builders-Bootcamp-7/tree/main) of the [AI Builders Bootcamp](https://maven.com/shaw-talebi/ai-builders-bootcamp).

## Requirements

- Python 3.13+
- A local LLM server (LM Studio, Ollama, etc.) OR OpenAI API key
- `uv` package manager (recommended)

## How to run this example

### Local LLM Version (Recommended for local development)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd yt-mcp-agent
   ```

2. **Install dependencies with uv**
   ```bash
   uv sync
   ```

3. **Set up your local LLM configuration**
   
   Create a `.env` file in the root directory:
   
   **For Ollama (recommended):**
   ```bash
   cat > .env << EOF
LOCAL_LLM_BASE_URL=http://localhost:11434/v1
LOCAL_LLM_API_KEY=ollama
LOCAL_LLM_MODEL=qwen3:4b
EOF
   ```
   
   **For LM Studio:**
   ```bash
   cat > .env << EOF
   LOCAL_LLM_BASE_URL=http://192.168.178.61:1234/v1
LOCAL_LLM_API_KEY=lm-studio
LOCAL_LLM_MODEL=qwen/qwen3-4b
EOF
   ```

4. **Run the local agent**
   ```bash
   uv run local_agent.py
   ```

5. **Interact with agent**
   
   Once running, you can ask the agent to analyze YouTube videos. Try prompts like:
   - "Summarize this: https://youtu.be/N3vHJcHBS-w?si=aw8PV0acYHJGPy7R"
   - "Generate chapter timestamps for this video: [URL]"
   - "Write me a LinkedIn post about this video: [URL]"

### Multi-step tool planning

- Type `reset` whenever you want to clear the conversation memory before giving a new request.
- The agent now reasons in steps: it can fetch web content, pull the right writing instructions, and then craft the final answer in one conversation turn.
- Each MCP tool call is streamed back to you so you can see the plan unfold (e.g., `fetch_web_content` → `fetch_instructions` → final draft).
- Keep prompts explicit about the desired output so the planner chooses the correct sequence of tools.

### Original OpenAI Version (requires OpenAI API access)

1. **Clone and install** (same as above)

2. **Set up OpenAI configuration**
   ```bash
   cat > .env << EOF
USE_OPENAI=true
OPENAI_API_KEY=your_api_key_here
EOF
   ```

3. **Run the original agent**
   ```bash
   uv run openai_agent.py
   ```

## Local LLMs Setup (for WSL users)

If you're running this in WSL and your LLM server is on Windows:

1. **Find your Windows host IP:**
   ```bash
   ip route show | grep default
   ```

2. **Update your `.env` file:**
   ```bash
   LOCAL_LLM_BASE_URL=http://YOUR_WINDOWS_IP:PORT/v1
   ```
   
   Example:
   ```bash
   LOCAL_LLM_BASE_URL=http://10.169.34.79:11434/v1  # Ollama
   LOCAL_LLM_BASE_URL=http://192.168.178.61:1234/v1  # LM Studio
   ```

### Supported Local LLM Servers

- **Ollama** (http://localhost:11434/v1) - Recommended
- **LM Studio** (http://localhost:1234/v1)
- **vLLM** (http://localhost:8000/v1)
- **Text Generation WebUI** (http://localhost:5000/v1)
- Any OpenAI-compatible server

**Note**: The local version uses basic OpenAI chat completions API, which most local LLM servers support well.

## Choosing Between Versions

| Feature | Local Version (`local_agent.py`) | OpenAI Version (`openai_agent.py`) |
|---------|--------------------------------|----------------------------|
| Local LLM Support | ✅ Full support | ❌ No (requires OpenAI Responses API) |
| OpenAI Support | ✅ Optional | ✅ Required |
| YouTube Transcripts | ✅ Yes | ✅ Yes |
| Content Generation | ✅ Yes | ✅ Yes |
| MCP Tools | ✅ Yes | ✅ Yes |
| Advanced Tracing | ❌ No | ✅ Yes (OpenAI platform) |
| Agent Handoffs | ❌ No | ❌ No |
| Setup Complexity | ✅ Simple | ⚠️ More complex |

## Base Python/pip Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd yt-mcp-agent
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e .
   ```

4. **Configure and run** (same as uv instructions above)

## Troubleshooting

### Local LLM Connection Issues
- Ensure your LLM server is running and accessible
- Check firewall settings if connecting across network
- Verify the correct IP address and port
- Test connection with: `curl http://YOUR_LLM_URL/v1/models`

### Model Selection
- Update `LOCAL_LLM_MODEL` in `.env` to match your available models
- List available models: `curl http://YOUR_LLM_URL/v1/models`

### WSL Network Issues
- Use Windows host IP instead of localhost
- Ensure LLM server accepts connections from all interfaces (0.0.0.0)