import asyncio
import os
import sys
from atp_translator import ATPTranslator
from mcp.client.stdio import StdioServerParameters
from crewai import Agent, Task, Crew, Process
from langchain_core.language_models.fake import FakeListLLM

async def main():
    print("Initializing ATP Translator...")
    translator = ATPTranslator(target_framework="crewai")
    
    # Path to the dummy server we just created
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
        print(f" - {tool.name} ({tool.description})")
        print(f"   Schema: {tool.args_schema.schema()}")
        
    print("\n--- Direct Tool Execution Test ---")
    sum_tool = next((t for t in tools if t.name == "calculate_sum"), None)
    if sum_tool:
        print("Executing calculate_sum tool directly to verify logging...")
        try:
            res = sum_tool._run(a=10, b=15)
            print(f"Result: {res}")
        except Exception as e:
            print(f"Tool execution failed: {e}")
            
    print("\nSetting up CrewAI Agent...")
    
    # Real LLM check
    if not os.environ.get("OPENAI_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
        print("API keys not found. Using a FakeListLLM for demonstration.")
        os.environ["OPENAI_API_KEY"] = "fake-key-for-testing"
        responses = [
            "Action: calculate_sum\nAction Input: {\"a\": 5, \"b\": 7}",
            "I have calculated the sum to be 12."
        ]
        llm = FakeListLLM(responses=responses)
    else:
        # Default CrewAI LLM (OpenAI mostly)
        llm = None
    
    agent = Agent(
        role='Math and Weather Assistant',
        goal='Accurately answer math questions and provide weather information.',
        backstory='You are a helpful assistant armed with tools to calculate sums and check weather.',
        verbose=True,
        allow_delegation=False,
        tools=tools,
        llm=llm
    )
    
    task = Task(
        description='Calculate the sum of 5 and 7, and find out the weather in Seattle.',
        expected_output='The final sum and weather report.',
        agent=agent
    )
    
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential
    )
    
    print("\nRunning CrewAI Task...")
    try:
        result = crew.kickoff()
        print("\n=== Final Result ===")
        print(result)
    except Exception as e:
        print(f"Error during execution: {e}")
    finally:
        print("Disconnecting from MCP Server...")
        await translator.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
