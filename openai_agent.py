from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServerStdio, MCPServer
from openai.types.responses import ResponseTextDeltaEvent
import asyncio

# import OPENAI_API_KEY from .env file
from dotenv import load_dotenv
import os
import ssl
load_dotenv()

# Configure LLM endpoint (local LLM by default, OpenAI as fallback)
if os.getenv("USE_OPENAI", "false").lower() == "true":
    # Use OpenAI's API
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is required when USE_OPENAI=true")
else:
    # Use local LLM by default (LM Studio)
    os.environ["OPENAI_BASE_URL"] = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:1234/v1")
    os.environ["OPENAI_API_KEY"] = os.getenv("LOCAL_LLM_API_KEY", "lm-studio")  # LM Studio accepts any key
    
    # Disable SSL verification for local connections
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context

async def main():
    async with MCPServerStdio(
        name="Content MCP Server",
        params={
            "command": "uv",
            "args": ["run", "mcp-server/content_mcp.py"],
        },
    ) as server:
        # Only use OpenAI tracing when using OpenAI's API
        use_openai = os.getenv("USE_OPENAI", "false").lower() == "true"
        
        if use_openai:
            trace_id = gen_trace_id()
            with trace(workflow_name="Content MCP Agent Example", trace_id=trace_id):
                print(f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}\n")
                await run(server)
        else:
            print("Using local LLM - OpenAI tracing disabled\n")
            await run(server)
        
async def run(mcp_server: MCPServer):
    # system prompt from MCP server
    prompt_result = await mcp_server.get_prompt("system_prompt")
    instructions = prompt_result.messages[0].content.text
    
    # create agent
    agent = Agent(
        name="Content Agent",
        instructions=instructions,
        mcp_servers=[mcp_server],
    )
    
    input_items = []

    print("=== Content Agent ===")
    print("Type 'exit' to end the conversation")
    print("Type 'reset' to clear context before a new request")

    while True:
        # Get user input
        user_input = input("\nUser: ").strip()
        
        # Check for exit command
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("\nGoodbye!")
            break

        if user_input.lower() in ['reset', 'clear', 'new']:
            input_items.clear()
            print("\n🔄 Conversation context cleared. Start with a new request.")
            continue
            
        if not user_input:
            continue

        input_items.append({"content": user_input, "role": "user"})

        result = Runner.run_streamed(
            agent,
            input=input_items,
        )
        print("\nAgent: ", end="", flush=True)
        
        async for event in result.stream_events():
            # We'll ignore the raw responses event deltas for text
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                print(event.data.delta, end="", flush=True)
            elif event.type == "run_item_stream_event":
                if event.item.type == "tool_call_item":
                    # Custom status messages for specific tools
                    tool_name = event.item.raw_item.name
                    if tool_name == "fetch_video_transcript":
                        status_msg = "\n-- Fetching transcript..."
                    elif tool_name == "fetch_instructions":
                        status_msg = "\n-- Fetching instructions..."
                    else:
                        status_msg = f"\n-- Calling {tool_name}..."
                    print(status_msg)
                elif event.item.type == "tool_call_output_item":
                    input_items.append({"content": f"{event.item.output}", "role": "user"})
                    print("-- Tool call completed.")
                elif event.item.type == "message_output_item":
                    input_items.append({"content": f"{event.item.raw_item.content[0].text}", "role": "assistant"})
                else:
                    pass  # Ignore other event types

        print("\n")  # Add a newline after each response

if __name__ == "__main__":
    asyncio.run(main())
