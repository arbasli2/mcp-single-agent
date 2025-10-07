#!/bin/bash
# YouTube MCP Agent Launcher
# This script helps you choose between the local LLM version and OpenAI version

echo "🎥 YouTube MCP Agent Launcher"
echo "=============================="
echo ""
echo "Choose your version:"
echo "1) Local LLM Version (works with LM Studio, Ollama, etc.)"
echo "2) OpenAI Version (requires OpenAI API key)"
echo "3) Exit"
echo ""

read -p "Enter your choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "🔧 Starting Local LLM Version..."
        echo "Make sure your local LLM server is running!"
        echo ""
        uv run main_local.py
        ;;
    2)
        echo ""
        echo "🌐 Starting OpenAI Version..."
        echo "Make sure you have OPENAI_API_KEY set!"
        echo ""
        uv run main.py
        ;;
    3)
        echo "Goodbye!"
        exit 0
        ;;
    *)
        echo "Invalid choice. Please run the script again."
        exit 1
        ;;
esac