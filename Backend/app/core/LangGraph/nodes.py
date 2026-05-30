import os
import asyncio
from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langchain_mcp_adapters.client import MultiServerMCPClient  
from langgraph.checkpoint.memory import InMemorySaver

from dotenv import load_dotenv
load_dotenv()

checkpointer = InMemorySaver()

OLLAMA_BASE_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "minimax-m2.1:cloud")
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))

ollama_llm = ChatOllama(
    base_url=OLLAMA_BASE_URL,
    model=OLLAMA_MODEL,
    temperature=OLLAMA_TEMPERATURE,
)

MCP_CONFIG = {}

_chat_agent_instance = None
_init_lock = asyncio.Lock()

async def get_agent(system_prompt):
    """Lazy initializer: creates agent on first call, waits if already creating."""
    global _chat_agent_instance
    if _chat_agent_instance is not None:
        return _chat_agent_instance
    async with _init_lock:
        if _chat_agent_instance is not None:
            return _chat_agent_instance
        client = MultiServerMCPClient(MCP_CONFIG)
        tools = await client.get_tools()
        _chat_agent_instance = create_agent(
            ollama_llm,
            system_prompt=system_prompt,
            tools=tools,
            checkpointer=checkpointer,
        )
        return _chat_agent_instance