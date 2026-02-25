import asyncio
from mcp.server.fastmcp import FastMCP

# Create a FastMCP server
mcp = FastMCP("DummyServer")

@mcp.tool()
def calculate_sum(a: int, b: int) -> int:
    """Calculates the sum of two integers."""
    return a + b

@mcp.tool()
def get_weather(location: str) -> str:
    """Gets the fictitious weather for a given location."""
    return f"The weather in {location} is sunny and 75 degrees."

if __name__ == "__main__":
    mcp.run(transport='stdio')
