# content-mcp-agent
A multi-purpose content agent built with a custom MCP server and OpenAI-compatible clients. It can pull YouTube transcripts, fetch reusable writing instructions, and scrape public webpages to support flexible content workflows.

Resources:
- [Talk recording](https://youtu.be/w-Ml3NivoFo)
- [Slides](https://drive.google.com/file/d/1id7V9nrNetW72k6vERS6oTy0bW0wEloo/view?usp=sharing)

> This example is a prelude to [Cohort 7](https://github.com/ShawhinT/AI-Builders-Bootcamp-7/tree/main) of the [AI Builders Bootcamp](https://maven.com/shaw-talebi/ai-builders-bootcamp).

## Requirements

- Python 3.13+
- A local LLM server (LM Studio, Ollama, etc.) **or** an OpenAI API key
- `uv` package manager (recommended)

## How to run this example

### uv (recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd content-mcp-agent
   ```

2. **Install dependencies with uv**
   ```bash
   uv sync
   ```

3. **Set up your API configuration**
   
   Create a `.env` file in the root directory:
   
   **For Local LLM (default - LM Studio):**
   ```bash
   cat > .env << EOF
LOCAL_LLM_BASE_URL=http://localhost:1234/v1
LOCAL_LLM_API_KEY=lm-studio
EOF
   ```
   
   **For OpenAI (alternative):**
   ```bash
   cat > .env << EOF
USE_OPENAI=true
OPENAI_API_KEY=your_api_key_here
EOF
   ```

4. **Run the agent**
   ```bash
   uv run openai_agent.py
   ```

5. **Interact with the agent**
   
   Once running, you can combine the available tools in one request. Sample prompts:
   - "Summarize this video and cite timecodes: https://youtu.be/N3vHJcHBS-w"
   - "Pull background facts from https://example.com and draft a LinkedIn post"
   - "Generate chapter timestamps and a blog outline for this talk"

### Base Python/pip

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd content-mcp-agent
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

4. **Set up your API configuration**
   
   Create a `.env` file in the root directory:
   
   **For Local LLM (default - LM Studio):**
   ```bash
   cat > .env << EOF
LOCAL_LLM_BASE_URL=http://localhost:1234/v1
LOCAL_LLM_API_KEY=lm-studio
EOF
   ```
   
   **For OpenAI (alternative):**
   ```bash
   cat > .env << EOF
USE_OPENAI=true
OPENAI_API_KEY=your_api_key_here
EOF
   ```

5. **Run the agent**
   ```bash
   python openai_agent.py
   ```

6. **Interact with the agent**
   - Ask for YouTube transcripts when you need video context
   - Fetch instructions before drafting blogs or social posts
   - Pull supporting material from web pages using the fetcher tool

## Using Local LLMs (Default)

This project uses local LLMs by default through OpenAI-compatible APIs. Here are some popular options:

### LM Studio (Default)
1. Download and install [LM Studio](https://lmstudio.ai/)
2. Download a model (e.g., Llama 3, Mistral, Code Llama)
3. Start the local server (default: `http://localhost:1234`)
4. The application will use LM Studio by default - no additional configuration needed!

**For WSL Users**: If you're running this in WSL and LM Studio is on Windows:
1. Find your Windows host IP: `ip route show | grep default`
2. Create a `.env` file with: `LOCAL_LLM_BASE_URL=http://YOUR_WINDOWS_IP:1234/v1`
3. Make sure LM Studio's server is configured to accept connections from all interfaces (0.0.0.0)

### Ollama
1. Install [Ollama](https://ollama.ai/)
2. Pull a model: `ollama pull llama3`
3. The API runs on `http://localhost:11434/v1`
4. Update `LOCAL_LLM_BASE_URL` in your `.env` file

### Other Options
- **vLLM**: High-performance inference server
- **Text Generation WebUI**: Web interface with API support
- **OpenAI-compatible servers**: Any server implementing OpenAI's API format

### Switching to OpenAI
To use OpenAI instead of a local LLM, set `USE_OPENAI=true` and provide your `OPENAI_API_KEY` in the `.env` file.

**Note**: Local LLMs may have different capabilities compared to OpenAI's models. Performance will depend on your hardware and the model size.
