#!/usr/bin/env python3
"""
YouTube MCP Agent - Local LLM Version
A simplified version that works with local LLMs (LM Studio, Ollama, etc.)
without requiring OpenAI's proprietary Agents SDK.
"""

import asyncio
import json
import os
import ssl
from typing import List, Dict, Any

from dotenv import load_dotenv
from openai import AsyncOpenAI
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

load_dotenv()

class LocalYouTubeAgent:
    def __init__(self):
        # Configure LLM endpoint
        if os.getenv("USE_OPENAI", "false").lower() == "true":
            # Use OpenAI's API
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError("OPENAI_API_KEY is required when USE_OPENAI=true")
            self.client = AsyncOpenAI()
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
            print(f"Using local LLM at: {base_url}")
        
        self.conversation_history: List[Dict[str, str]] = []
        self.mcp_session = None
        self.system_instructions = ""
        
    async def start_mcp_server(self):
        """Start the MCP server and get system instructions"""
        server_params = StdioServerParameters(
            command="uv",
            args=["run", "mcp-server/yt-mcp.py"]
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
                            self.system_instructions = prompt_result.messages[0].content.text
                            print(f"✅ Using system instructions from MCP server")
                            print(f"📝 System prompt: {self.system_instructions[:100]}{'...' if len(self.system_instructions) > 100 else ''}")
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
                if hasattr(content, 'text'):
                    return content.text
                else:
                    return str(content)
            return "Tool executed but returned no content"
        except Exception as e:
            return f"Error calling tool {tool_name}: {str(e)}"

    async def process_message(self, user_input: str) -> str:
        """Process a user message and return the assistant's response"""
        # Add user message to conversation history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # First, let the LLM decide what tools (if any) it needs to use
        tool_decision = await self.decide_tools_needed(user_input)
        
        # Execute any tools the LLM requested
        tool_results = []
        if tool_decision.get("tools_needed"):
            for tool_call in tool_decision["tools_needed"]:
                tool_name = tool_call["name"]
                tool_args = tool_call["arguments"]
                
                print(f"-- Calling {tool_name}...")
                result = await self.call_mcp_tool(tool_name, tool_args)
                tool_results.append({
                    "tool": tool_name,
                    "result": result
                })
        
        # Prepare messages for the final LLM call
        messages = [{"role": "system", "content": self.system_instructions}]
        messages.extend(self.conversation_history)
        
        # Add tool results to context if any
        if tool_results:
            tool_context = "Tool execution results:\n\n"
            for tr in tool_results:
                tool_context += f"Tool: {tr['tool']}\nResult: {tr['result']}\n\n"
            messages.append({"role": "user", "content": tool_context})
        
        try:
            # Call the LLM for the final response
            response = await self.client.chat.completions.create(
                model=self.get_model_name(),
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            assistant_response = response.choices[0].message.content
            
            # Add assistant response to conversation history
            self.conversation_history.append({"role": "assistant", "content": assistant_response})
            
            return assistant_response
            
        except Exception as e:
            return f"Error: {str(e)}"

    async def decide_tools_needed(self, user_input: str) -> dict:
        """Use Ollama's native function calling to decide what tools are needed"""
        
        # Get available tools from MCP server
        available_tools = await self.get_available_tools_for_function_calling()
        
        if not available_tools:
            return {"tools_needed": []}
        
        try:
            # Use OpenAI-compatible function calling with Ollama
            print(f"-- Checking if tools are needed for: '{user_input}'")
            print(f"-- Available tools count: {len(available_tools)}")
            
            response = await self.client.chat.completions.create(
                model=self.get_model_name(),
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a helpful assistant that can call functions to help users. Analyze the user's request and call appropriate functions if needed."
                    },
                    {
                        "role": "user", 
                        "content": user_input
                    }
                ],
                tools=available_tools,
                tool_choice="auto",  # Let the model decide whether to call tools
                temperature=0.1,
                max_tokens=500
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

    async def get_available_tools_for_function_calling(self) -> list:
        """Get MCP tools formatted for OpenAI function calling"""
        if not self.mcp_session:
            print("❌ No MCP session - no tools available")
            return []
        
        try:
            # Get list of available tools from MCP server
            tools_result = await self.mcp_session.list_tools()
            
            print(f"🔧 Found {len(tools_result.tools)} MCP tools:")
            function_tools = []
            for tool in tools_result.tools:
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

    def get_model_name(self) -> str:
        """Get the appropriate model name based on the LLM provider"""
        if os.getenv("USE_OPENAI", "false").lower() == "true":
            return "gpt-4o-mini"  # Default OpenAI model
        else:
            # For local LLMs, try to detect a good model
            # You can customize this based on your available models
            return os.getenv("LOCAL_LLM_MODEL", "qwen3:4b")

    def extract_urls_from_text(self, text: str) -> List[str]:
        """Extract URLs from text using regex - generic utility"""
        import re
        url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?'
        urls = re.findall(url_pattern, text)
        return urls

    async def run_conversation_loop(self):
        """Main conversation loop"""
        print("=== YouTube Agent (Local LLM Version) ===")
        print("Type 'exit' to end the conversation")
        print()
        
        while True:
            try:
                # Get user input
                user_input = input("User: ").strip()
                
                # Check for exit command
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("\nGoodbye!")
                    break
                
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
    agent = LocalYouTubeAgent()
    await agent.start_mcp_server()

if __name__ == "__main__":
    asyncio.run(main())