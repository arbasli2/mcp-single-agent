# yt-mcp-agent
A YouTube video agent built using a custom MCP server and OpenAI's Agent's SDK. It can extract video transcripts given link fetch specialized instructions for things like: writing blog posts, video chapters, and social posts.

Resources:
- [Talk recording](https://youtu.be/w-Ml3NivoFo)
- [Slides](https://drive.google.com/file/d/1id7V9nrNetW72k6vERS6oTy0bW0wEloo/view?usp=sharing)

>This example is a prelude to [Cohort 7](https://github.com/ShawhinT/AI-Builders-Bootcamp-7/tree/main) of the [AI Builders Bootcamp](https://maven.com/shaw-talebi/ai-builders-bootcamp).

## Requirements

- Python 3.13+
- A local LLM server (LM Studio, Ollama, etc.) OR OpenAI API key
- `uv` package manager (recommended)

## How to run this example

### uv (recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd yt-mcp-agent
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

5. **Interact with agent**
   
   Once running, you can ask the agent to analyze YouTube videos. Try prompts like:
   - "Summarize this: https://youtu.be/N3vHJcHBS-w?si=aw8PV0acYHJGPy7R"
   - "Generate chapter timestamps with links"
   - "Write me a LinkedIn post about the video"

### Base Python/pip

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

6. **Interact with agent**

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
