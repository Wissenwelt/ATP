import asyncio
import os
import sys
from atp_translator import ATPTranslator
from mcp.client.stdio import StdioServerParameters

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core.tools import FunctionTool

async def main():
    print("Initializing ATP Translator for AutoGen...")
    translator = ATPTranslator(target_framework="autogen")
    
    python_executable = sys.executable
    server_script = os.path.join(os.path.dirname(__file__), "dummy_mcp_server.py")
    
    server_parameters = StdioServerParameters(
        command=python_executable,
        args=[server_script],
        env=None
    )
    
    print("Connecting to Dummy MCP Server...")
    await translator.connect(server_parameters)
    
    print("Fetching tools from MCP Server...")
    tools = await translator.get_tools()
    
    print(f"Discovered {len(tools)} tools:")
    for tool in tools:
        print(f" - {tool.name}")
        
    print("\n--- Direct Tool Execution Test for AutoGen ---")
    sum_tool = next((t for t in tools if t.name == "calculate_sum"), None)
    if sum_tool:
        print("Executing calculate_sum tool directly to verify logging...")
        try:
            # For BaseTool, we pass a pydantic model instance of args_type
            res = await sum_tool.run(sum_tool.args_type()(a=20, b=30), cancellation_token=None)
            print(f"Result: {res}")
        except Exception as e:
            print(f"Tool execution failed: {e}")

    # Set up AutoGen 0.4 agent config
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY"):
        print("\nSetting up AutoGen Agents...")
        
        # Instantiate model client using OpenAI compatible interface for either OpenAI or Gemini
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        
        api_key = os.environ.get("OPENAI_API_KEY")
        model = "gpt-4-turbo"
        base_url = None
        if not api_key:
            # Fallback to Gemini if native key is not there but GEMINI is. Gemini exposes an OpenAI compatible API
            api_key = os.environ.get("GEMINI_API_KEY")
            model = "gemini-1.5-flash"
            base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
             
        model_client = OpenAIChatCompletionClient(
            model=model,
            api_key=api_key,
            base_url=base_url
        )

        assistant = AssistantAgent(
            name="Assistant",
            system_message="You are a helpful assistant. Use the provided tools. Conclude your final answer with 'TERMINATE'.",
            model_client=model_client,
            tools=tools
        )
        
        termination = TextMentionTermination("TERMINATE")
        team = RoundRobinGroupChat([assistant], termination_condition=termination)
        
        print("\nRunning AutoGen Task...")
        try:
            from autogen_agentchat.ui import Console
            await Console(team.run_stream(task="Calculate the sum of 15 and 27, then check the weather in Boston."))
        except Exception as e:
            print(f"Error during execution: {e}")
    else:
        print("\nAPI keys not found. AutoGen LLM chat test skipped (direct execution succeeded).")
        print("To run the full conversation, please set GEMINI_API_KEY.")
            
    print("Disconnecting from MCP Server...")
    await translator.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
