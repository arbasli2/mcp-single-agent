#!/usr/bin/env python3
"""
Content MCP Agent - Local LLM Version
A simplified version that works with local LLMs (LM Studio, Ollama, etc.)
without requiring OpenAI's proprietary Agents SDK.
"""

import asyncio
import json
import os
import re
import ssl
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

load_dotenv()

class LocalContentAgent:
    def __init__(self):
        # Configure LLM endpoint
        self.using_openai = os.getenv("USE_OPENAI", "false").lower() == "true"
        if self.using_openai:
            # Use OpenAI's API
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError("OPENAI_API_KEY is required when USE_OPENAI=true")
            self.client = AsyncOpenAI()
            self.llm_endpoint = "https://api.openai.com/v1"
        else:
            # Use local LLM by default
            base_url = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:1234/v1")
            api_key = os.getenv("LOCAL_LLM_API_KEY", "local")
            
            # Disable SSL verification for local connections
            ssl._create_default_https_context = ssl._create_unverified_context
            
            self.client = AsyncOpenAI(
                base_url=base_url,
                api_key=api_key
            )
            self.llm_endpoint = base_url
            print(f"Using local LLM at: {base_url}")
        
        self.conversation_history: List[Dict[str, str]] = []
        self.mcp_session = None
        self.system_instructions = ""
        
    def reset_conversation(self) -> None:
        """Clear the running conversation history so the next turn is fresh."""
        self.conversation_history.clear()
        print("\n🔄 Conversation context cleared. Start with a new request.\n")

    async def start_mcp_server(self):
        """Start the MCP server and get system instructions"""
        server_params = StdioServerParameters(
            command="uv",
            args=["run", "mcp-server/content_mcp.py"]
        )
        
        print("🚀 Starting MCP server...")
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    self.mcp_session = session
                    
                    # Initialize the session
                    print("🔌 Initializing MCP session...")
                    await session.initialize()
                    print("✅ MCP session initialized successfully")
                    
                    # Get system instructions
                    try:
                        prompt_result = await session.get_prompt("system_prompt")
                        if prompt_result and hasattr(prompt_result, 'messages') and prompt_result.messages:
                            first_content = prompt_result.messages[0].content
                            system_text = getattr(first_content, "text", "") if first_content else ""
                            self.system_instructions = system_text or ""
                            print("✅ Using system instructions from MCP server")
                            if self.system_instructions:
                                preview = self.system_instructions[:100]
                                ellipsis = "..." if len(self.system_instructions) > 100 else ""
                                print(f"📝 System prompt: {preview}{ellipsis}")
                            else:
                                print("📝 System prompt unavailable - proceeding without it")
                        else:
                            self.system_instructions = ""
                            print("⚠️  No system prompt provided by MCP server - running with no system instructions")
                    except Exception as e:
                        print(f"❌ Could not get system prompt from MCP server: {e}")
                        self.system_instructions = ""
                        print("🔄 Running with no system instructions")
                    
                    # Run the main conversation loop
                    await self.run_conversation_loop()
                    
        except Exception as e:
            print(f"❌ Error starting MCP server: {e}")
            print("🔄 Running without MCP tools...")
            await self.run_conversation_loop()

    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call an MCP tool and return the result"""
        if not self.mcp_session:
            return f"Error: MCP server not available"
        
        try:
            result = await self.mcp_session.call_tool(tool_name, arguments)
            if result and hasattr(result, 'content') and result.content:
                # Handle different content types
                content = result.content[0]
                text_value = getattr(content, "text", None)
                if isinstance(text_value, str):
                    return text_value
                else:
                    return str(content)
            return "Tool executed but returned no content"
        except Exception as e:
            return f"Error calling tool {tool_name}: {str(e)}"

    async def process_message(self, user_input: str) -> str:
        """Process a user message and support multi-step MCP tool plans."""
        # Add the incoming user turn to the running history
        self.conversation_history.append({"role": "user", "content": user_input})

        # Construct the working message list that will be sent to the model
        messages: List[Dict[str, Any]] = []
        if self.system_instructions:
            messages.append({"role": "system", "content": self.system_instructions})
        messages.extend(self.conversation_history)

        available_tools = await self.get_available_tools_for_function_calling(user_input)

        assistant_response: str = ""
        recent_tool_calls: List[str] = []  # Track recent tool calls to detect loops

        try:
            while True:
                request_payload: Dict[str, Any] = {
                    "model": self.get_model_name(),
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 2000,
                }
                if available_tools:
                    request_payload["tools"] = available_tools
                    request_payload["tool_choice"] = "auto"

                response = await self._create_chat_completion(request_payload)
                first_choice = self._select_first_choice(response)
                message = getattr(first_choice, "message", None)
                if message is None:
                    raise RuntimeError(self._format_missing_message_error(response))

                content_text = message.content or ""
                assistant_message: Dict[str, Any] = {"role": "assistant", "content": content_text}

                tool_calls = getattr(message, "tool_calls", None)
                if tool_calls and available_tools:
                    # Check for repeated identical tool calls (potential infinite loop)
                    current_calls = []
                    for tool_call in tool_calls:
                        function_obj = getattr(tool_call, "function", None)
                        if function_obj:
                            function_name = getattr(function_obj, "name", "")
                            raw_arguments = getattr(function_obj, "arguments", "{}")
                        else:
                            function_name = getattr(tool_call, "name", "")
                            raw_arguments = getattr(tool_call, "arguments", "{}")
                        
                        call_signature = f"{function_name}({raw_arguments})"
                        current_calls.append(call_signature)
                    
                    # If we've seen these exact calls recently, break the loop
                    if current_calls == recent_tool_calls:
                        print("⚠️  Detected repeated identical tool calls. Breaking loop to prevent infinite recursion.")
                        assistant_response = content_text or "I was able to fetch the information but encountered an issue processing it. Please try a different approach or rephrase your request."
                        break
                    
                    recent_tool_calls = current_calls
                    
                    # Capture the assistant tool call for the conversation trace
                    serialized_calls: List[Dict[str, Any]] = []
                    tool_results_messages: List[Dict[str, Any]] = []

                    for tool_call in tool_calls:
                        function_obj = getattr(tool_call, "function", None)
                        call_id = getattr(tool_call, "id", "")
                        if function_obj:
                            function_name = getattr(function_obj, "name", "")
                            raw_arguments = getattr(function_obj, "arguments", "{}")
                        else:
                            function_name = getattr(tool_call, "name", "")
                            raw_arguments = getattr(tool_call, "arguments", "{}")

                        try:
                            parsed_arguments = json.loads(raw_arguments or "{}")
                        except json.JSONDecodeError:
                            parsed_arguments = {}

                        print(f"-- Calling {function_name}...")
                        tool_output = await self.call_mcp_tool(function_name, parsed_arguments)
                        print(f"-- Tool completed: {len(tool_output)} characters returned")

                        serialized_calls.append({
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": function_name,
                                "arguments": json.dumps(parsed_arguments),
                            },
                        })

                        tool_results_messages.append({
                            "role": "tool",
                            "tool_call_id": call_id,
                            "name": function_name,
                            "content": tool_output,
                        })

                    assistant_message["tool_calls"] = serialized_calls
                    messages.append(assistant_message)
                    messages.extend(tool_results_messages)
                    
                    # Debug: Print current conversation state
                    print(f"-- Added {len(tool_results_messages)} tool result(s) to conversation")
                    print(f"-- Current conversation has {len(messages)} messages")
                    
                    # Continue the loop so the model can react to tool output
                    continue

                # No further tool use requested; finalize the assistant response
                print("-- Model provided final response (no more tool calls)")
                messages.append(assistant_message)
                assistant_response = content_text
                break

            # Record the final assistant turn for future dialogue context
            self.conversation_history.append({"role": "assistant", "content": assistant_response})

            return assistant_response

        except Exception as e:
            return f"Error: {str(e)}"

    async def decide_tools_needed(self, user_input: str) -> dict:
        """Use Ollama's native function calling to decide what tools are needed"""
        
        # Get available tools from MCP server
        available_tools = await self.get_available_tools_for_function_calling(user_input)
        
        if not available_tools:
            return {"tools_needed": []}
        
        try:
            # Use OpenAI-compatible function calling with Ollama
            print(f"-- Checking if tools are needed for: '{user_input}'")
            print(f"-- Available tools count: {len(available_tools)}")
            
            response = await self._create_chat_completion(
                {
                    "model": self.get_model_name(),
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a helpful assistant that can call functions to help users. "
                                "Analyze the user's request and call appropriate functions if needed."
                            ),
                        },
                        {
                            "role": "user",
                            "content": user_input,
                        },
                    ],
                    "tools": available_tools,
                    "tool_choice": "auto",
                    "temperature": 0.1,
                    "max_tokens": 500,
                }
            )
            
            print(f"-- Model response tool_calls: {response.choices[0].message.tool_calls}")
            
            # Check if the model wants to call any tools
            if response.choices[0].message.tool_calls:
                print("-- Model wants to call tools!")
                tools_needed = []
                for tool_call in response.choices[0].message.tool_calls:
                    # Handle different tool call structures safely
                    try:
                        # Try function attribute first (standard OpenAI format)
                        function_obj = getattr(tool_call, 'function', None)
                        if function_obj:
                            function_name = getattr(function_obj, 'name', 'unknown')
                            function_args_str = getattr(function_obj, 'arguments', '{}')
                            function_args = json.loads(function_args_str)
                        else:
                            # Direct tool call structure (alternative format)
                            function_name = getattr(tool_call, 'name', 'unknown')
                            function_args = getattr(tool_call, 'arguments', {})
                            if isinstance(function_args, str):
                                function_args = json.loads(function_args)
                        
                        print(f"-- Parsed tool call: {function_name} with args: {function_args}")
                        tools_needed.append({
                            "name": function_name,
                            "arguments": function_args,
                            "reason": f"Model decided to call {function_name}"
                        })
                    except Exception as e:
                        print(f"Warning: Could not parse tool call: {e}")
                        continue
                        
                return {"tools_needed": tools_needed}
            else:
                print("-- Model chose not to call any tools")
                return {"tools_needed": []}
                
        except Exception as e:
            print(f"Error in function calling: {e}")
            # If function calling fails, just return no tools
            return {"tools_needed": []}

    async def get_available_tools_for_function_calling(self, user_input: Optional[str] = None) -> list:
        """Get MCP tools formatted for OpenAI function calling"""
        if not self.mcp_session:
            print("❌ No MCP session - no tools available")
            return []
        
        try:
            # Get list of available tools from MCP server
            tools_result = await self.mcp_session.list_tools()
            
            print(f"🔧 Found {len(tools_result.tools)} MCP tools:")
            function_tools = []
            has_youtube_url = self._contains_youtube_url(user_input or "") if user_input is not None else True

            for tool in tools_result.tools:
                if tool.name == "fetch_video_transcript" and user_input is not None and not has_youtube_url:
                    print("   • Skipping fetch_video_transcript - no YouTube URL detected")
                    continue
                print(f"   • {tool.name}: {tool.description}")
                # Convert MCP tool to OpenAI function format
                function_def = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema if hasattr(tool, 'inputSchema') and tool.inputSchema else {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                }
                function_tools.append(function_def)
            
            print(f"✅ Converted {len(function_tools)} tools for function calling")
            return function_tools
            
        except Exception as e:
            print(f"❌ Could not get MCP tools for function calling: {e}")
            return []

    async def _create_chat_completion(self, payload: Dict[str, Any]) -> Any:
        """Send a chat completion request with basic retry handling for transient errors."""
        max_attempts = 3
        last_exception: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            try:
                return await self.client.chat.completions.create(**payload)
            except Exception as exc:  # noqa: BLE001 - treat all exceptions as potentially transient
                last_exception = exc
                message = str(exc).lower()
                is_retryable = any(keyword in message for keyword in ["connection", "timeout", "temporar", "reset"])
                if not is_retryable:
                    raise RuntimeError(self._format_non_retryable_error(exc)) from exc
                if attempt == max_attempts:
                    break
                await asyncio.sleep(min(2, attempt))

        if last_exception is not None:
            raise RuntimeError(self._format_connection_failure(last_exception, max_attempts)) from last_exception

    def _format_non_retryable_error(self, error: Exception) -> str:
        """Return a helpful message for non-retryable LLM errors."""
        if self.using_openai:
            hint = "Recheck your OpenAI API key, selected model, or request parameters."
        else:
            hint = (
                "Verify the local model name in LOCAL_LLM_MODEL or set USE_OPENAI=true "
                "to use the OpenAI API instead."
            )
        return f"LLM request failed: {error}. {hint}"

    def _format_connection_failure(self, error: Exception, attempts: int) -> str:
        """Return user-facing guidance when we cannot reach the LLM endpoint."""
        if self.using_openai:
            hint = "Confirm network access to OpenAI and that your API key is valid."
        else:
            hint = (
                f"Ensure a local LLM server is running at {self.llm_endpoint}, or set USE_OPENAI=true "
                "to fall back to the OpenAI API."
            )
        return (
            f"Unable to reach the LLM endpoint at {self.llm_endpoint} after {attempts} attempts. "
            f"Original error: {error}. {hint}"
        )

    def _select_first_choice(self, response: Any) -> Any:
        """Return the first completion choice or raise a helpful error."""
        choices = getattr(response, "choices", None)
        if not choices:
            raise RuntimeError(self._format_missing_choices_error(response))
        first_choice = choices[0]
        if first_choice is None:
            raise RuntimeError(self._format_missing_choices_error(response))
        return first_choice

    def _format_missing_choices_error(self, response: Any) -> str:
        """Build guidance when the LLM returns no usable choices."""
        base = "LLM returned no choices."
        if self.using_openai:
            hint = (
                "Validate the requested OpenAI model and inspect platform logs for errors."
            )
        else:
            hint = (
                "Check the local LLM server logs and confirm it supports the Chat Completions API."
            )
        return f"{base} Raw response: {response}. {hint}"

    def _format_missing_message_error(self, response: Any) -> str:
        """Build guidance when the LLM choice is missing a message payload."""
        base = "LLM returned a choice without a message payload."
        if self.using_openai:
            hint = "Inspect the response on the OpenAI dashboard; the model may not support tools."
        else:
            hint = (
                "Verify the local server's response schema matches OpenAI's Chat Completions format."
            )
        return f"{base} Raw response: {response}. {hint}"

    def _contains_youtube_url(self, text: str) -> bool:
        """Return True when text includes a YouTube URL."""
        pattern = r"https?://(?:www\.)?(?:youtube\.com|youtu\.be)/"
        return bool(re.search(pattern, text))

    def get_model_name(self) -> str:
        """Get the appropriate model name based on the LLM provider"""
        if os.getenv("USE_OPENAI", "false").lower() == "true":
            return "gpt-4o-mini"  # Default OpenAI model
        else:
            # For local LLMs, try to detect a good model
            # You can customize this based on your available models
            return os.getenv("LOCAL_LLM_MODEL", "qwen3:4b-2507")

    def extract_urls_from_text(self, text: str) -> List[str]:
        """Extract URLs from text using regex - generic utility"""
        import re
        url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_\.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?'
        urls = re.findall(url_pattern, text)
        return urls

    async def run_conversation_loop(self):
        """Main conversation loop"""
        print("=== Content Agent (Local LLM Version) ===")
        print("Type 'exit' to end the conversation")
        print("Type 'reset' to clear context before a new request")
        print()
        
        while True:
            try:
                # Get user input
                user_input = input("User: ").strip()
                
                # Check for exit command
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("\nGoodbye!")
                    break
                
                if user_input.lower() in ['reset', 'clear', 'new']:
                    self.reset_conversation()
                    continue

                if not user_input:
                    continue
                
                # Process the message
                print("\nAgent: ", end="", flush=True)
                response = await self.process_message(user_input)
                print(response)
                print()
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}")
                print()

async def main():
    """Main entry point"""
    agent = LocalContentAgent()
    await agent.start_mcp_server()

if __name__ == "__main__":
    asyncio.run(main())
