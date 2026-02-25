import asyncio
import json
from typing import Any, Dict, List, Type, Optional
from pydantic import BaseModel, create_model, Field

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
import mcp.types as types

# CrewAI imports
from crewai.tools import BaseTool

class ATPTranslator:
    """
    Agent Tool Protocol (ATP) Translator.
    Connects to an MCP server, fetches its tools, and dynamically generates
    compatible tool instances for agent frameworks (e.g., CrewAI).
    """

    def __init__(self, target_framework: str = "crewai"):
        self.target_framework = target_framework.lower()
        self.server_params = None
        self._exit_stack = None
        self.session: Optional[ClientSession] = None
        self._stdio_ctx = None

    async def connect(self, server_parameters: StdioServerParameters):
        """Establishes a connection to the MCP server."""
        self.server_params = server_parameters
        
        # We need to manage the context managers manually since we want to keep the session open
        from contextlib import AsyncExitStack
        self._exit_stack = AsyncExitStack()
        
        self._stdio_ctx = stdio_client(self.server_params)
        read, write = await self._exit_stack.enter_async_context(self._stdio_ctx)
        
        self.session = await self._exit_stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()
        print(f"Connected to MCP Server with params: {self.server_params.command}")

    async def disconnect(self):
        """Closes the connection to the MCP server."""
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
            self.session = None

    async def get_tools(self) -> List[Any]:
        """Fetches tools from the MCP server and translates them to the target framework."""
        if not self.session:
            raise RuntimeError("Not connected to an MCP server. Call connect() first.")

        response = await self.session.list_tools()
        tools = []
        
        # Setup DB Session
        try:
            from db import init_db, generate_manifest_hash, ATPToolRegistry
            _, SessionLocal = init_db()
            db_session = SessionLocal()
        except ImportError:
            print("DB registry not available. Tools will not be registered.")
            db_session = None
        
        try:
            for mcp_tool in response.tools:
                # Register tool if DB available
                if db_session:
                    try:
                        # Attempt to derive server name; for stdio it's the command, otherwise 'Unknown'
                        server_name = self.server_params.command if self.server_params else "Unknown"
                        schema_dict = mcp_tool.inputSchema
                        
                        m_hash = generate_manifest_hash(server_name, mcp_tool.name, schema_dict)
                        
                        existing_tool = db_session.query(ATPToolRegistry).filter_by(manifest_hash=m_hash).first()
                        if not existing_tool:
                            # Use generated python code string representation for context
                            pydantic_code = self._generate_pydantic_model(mcp_tool.name, schema_dict).schema_json()
                            
                            new_entry = ATPToolRegistry(
                                mcp_server_name=server_name,
                                tool_name=mcp_tool.name,
                                manifest_hash=m_hash,
                                raw_mcp_schema=schema_dict,
                                pydantic_schema_code=pydantic_code
                            )
                            db_session.add(new_entry)
                            db_session.commit()
                    except Exception as e:
                        print(f"Failed to register tool {mcp_tool.name}: {e}")
                
                # Perform translation
                if self.target_framework == "crewai":
                    translated_tool = self._generate_crewai_tool(mcp_tool)
                    tools.append(translated_tool)
                elif self.target_framework == "langchain":
                    translated_tool = self._generate_langchain_tool(mcp_tool)
                    tools.append(translated_tool)
                elif self.target_framework == "autogen":
                    translated_tool = self._generate_autogen_tool(mcp_tool)
                    tools.append(translated_tool)
                else:
                    raise ValueError(f"Unsupported target framework: {self.target_framework}")
        finally:
            if db_session:
                db_session.close()
                
        return tools

    def _json_schema_to_pydantic_type(self, schema: Dict[str, Any]) -> Type:
        """Converts a JSON schema type to a Python/Pydantic type."""
        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        schema_type = schema.get("type", "string")
        return type_mapping.get(schema_type, Any)

    def _generate_pydantic_model(self, tool_name: str, input_schema: Dict[str, Any]) -> Type[BaseModel]:
        """Dynamically generates a Pydantic model from an MCP JSON schema."""
        fields = {}
        properties = input_schema.get("properties", {})
        required_fields = input_schema.get("required", [])

        for field_name, field_schema in properties.items():
            field_type = self._json_schema_to_pydantic_type(field_schema)
            description = field_schema.get("description", "")
            
            if field_name in required_fields:
                fields[field_name] = (field_type, Field(..., description=description))
            else:
                # Optional field
                fields[field_name] = (Optional[field_type], Field(default=None, description=description))

        model_name = f"{tool_name.capitalize()}Input"
        return create_model(model_name, **fields)

    def _generate_langchain_tool(self, mcp_tool: types.Tool) -> Any:
        try:
            from langchain_core.tools import StructuredTool
        except ImportError:
            raise ImportError("langchain-core is required to generate LangChain tools. Run `pip install langchain-core`.")
        
        generated_schema = self._generate_pydantic_model(mcp_tool.name, mcp_tool.inputSchema)
        session = self.session
        
        async def _arun(**kwargs) -> str:
            """Asynchronous execution for LangChain."""
            result = await session.call_tool(mcp_tool.name, arguments=kwargs)
            
            is_anomaly = False
            output = ""
            if result.isError:
                is_anomaly = True
                output = f"Error executing tool: {result.content}"
            else:
                for content in result.content:
                    if content.type == "text":
                        output += content.text
            
            import httpx
            import json
            try:
                # Safely encode arguments for the SQLite JSON column fallback
                safe_kwargs = json.loads(json.dumps(kwargs))
                async with httpx.AsyncClient() as client:
                    payload = {
                        "tool_name": mcp_tool.name,
                        "agent_framework": "langchain",
                        "input_arguments": safe_kwargs,
                        "execution_result": output,
                        "is_anomaly": is_anomaly
                    }
                    await client.post("http://127.0.0.1:8000/logs", json=payload, timeout=5.0)
            except Exception as e:
                print(f"Failed to record LangChain execution log via API: {e}")

            return output

        def _run(**kwargs) -> str:
            """Synchronous execution fallback for LangChain."""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(_arun(**kwargs))
            finally:
                loop.close()

        return StructuredTool(
            name=mcp_tool.name,
            description=mcp_tool.description or f"Tool to execute {mcp_tool.name}",
            args_schema=generated_schema,
            func=_run,
            coroutine=_arun
        )

    def _generate_crewai_tool(self, mcp_tool: types.Tool) -> BaseTool:
        """Generates a CrewAI BaseTool from an MCP Tool."""
        generated_schema = self._generate_pydantic_model(mcp_tool.name, mcp_tool.inputSchema)
        
        # We need a reference to the active session to call the tool
        session = self.session
        
        class DynamicCrewAITool(BaseTool):
            name: str = mcp_tool.name
            description: str = mcp_tool.description or f"Tool to execute {mcp_tool.name}"
            args_schema: Type[BaseModel] = generated_schema
            
            def _run(self, **kwargs) -> str:
                """CrewAI expects synchronous execution by default, but MCP is async. 
                We use asyncio.run to bridge the gap if there's no running loop, 
                or run_until_complete if there is. For robust usage, wrap in a thread or use run_coroutine_threadsafe."""
                
                async def _async_call():
                    result = await session.call_tool(self.name, arguments=kwargs)
                    
                    is_anomaly = False
                    output = ""
                    if result.isError:
                        is_anomaly = True
                        output = f"Error executing tool: {result.content}"
                    else:
                        for content in result.content:
                            if content.type == "text":
                                output += content.text
                    
                    # Log execution via HTTP to avoid thread/SQLite lock issues
                    import httpx
                    import json
                    try:
                        async with httpx.AsyncClient() as client:
                            payload = {
                                "tool_name": mcp_tool.name,
                                "agent_framework": "crewai",
                                "input_arguments": kwargs,
                                "execution_result": output,
                                "is_anomaly": is_anomaly
                            }
                            await client.post("http://127.0.0.1:8000/logs", json=payload, timeout=5.0)
                    except Exception as e:
                        print(f"Failed to record CrewAI execution log via API: {e}")

                    return output

                try:
                    # In a typical CrewAI setup, _run is called synchronously.
                    # We create a new event loop just for this call since it might be executed in a thread pool by CrewAI.
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(_async_call())
                    finally:
                        loop.close()
                except Exception as e:
                    return f"Exception bridging sync to async: {str(e)}"

        return DynamicCrewAITool()

    def _generate_autogen_tool(self, mcp_tool: types.Tool) -> Any:
        """Generates an AutoGen compatible tool schema and execution callable."""
        try:
            from autogen_core.tools import BaseTool
            from autogen_core import CancellationToken
        except ImportError:
            raise ImportError("autogen-core is required to generate AutoGen tools. Run `pip install autogen-core`.")
            
        generated_schema = self._generate_pydantic_model(mcp_tool.name, mcp_tool.inputSchema)
        session = self.session
        
        async def _async_call(**kwargs):
            result = await session.call_tool(mcp_tool.name, arguments=kwargs)
            
            is_anomaly = False
            output = ""
            if result.isError:
                is_anomaly = True
                output = f"Error executing tool: {result.content}"
            else:
                for content in result.content:
                    if content.type == "text":
                        output += content.text
            
            import httpx
            import json
            try:
                safe_kwargs = json.loads(json.dumps(kwargs))
                async with httpx.AsyncClient() as client:
                    payload = {
                        "tool_name": mcp_tool.name,
                        "agent_framework": "autogen",
                        "input_arguments": safe_kwargs,
                        "execution_result": output,
                        "is_anomaly": is_anomaly
                    }
                    await client.post("http://127.0.0.1:8000/logs", json=payload, timeout=5.0)
            except Exception as e:
                print(f"Failed to record AutoGen execution log via API: {e}")

            return output

        class DynamicAutoGenTool(BaseTool):
            def __init__(self):
                super().__init__(
                    args_type=generated_schema,
                    return_type=str,
                    name=mcp_tool.name,
                    description=mcp_tool.description or f"Tool {mcp_tool.name}"
                )
                
            async def run(self, args: BaseModel, cancellation_token: CancellationToken) -> str:
                kwargs = args.model_dump()
                return await _async_call(**kwargs)

        return DynamicAutoGenTool()
