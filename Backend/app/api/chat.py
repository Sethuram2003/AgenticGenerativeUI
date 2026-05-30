from fastapi import APIRouter
import logging
import json
import uuid
from pydantic import BaseModel

from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from dotenv import load_dotenv
load_dotenv()

from app.core.LangGraph.nodes import get_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

class ChatRequest(BaseModel):
    messages: list[dict]
    systemPrompt: str | None = None

@router.post("/chat")
async def chat(request: ChatRequest):
    return StreamingResponse(
        stream_langgraph_native(request.messages, request.systemPrompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
        },
    )

async def stream_langgraph_native(messages: list[dict], system_prompt: str | None):
    """
    Stream assistant response using LangGraph's native event format.
    The frontend `langGraphAdapter` expects:
      - event: messages   (json list of LangChain message chunks)
      - event: end        (completion signal)
    """
    langchain_messages = []
    if system_prompt:
        langchain_messages.append(SystemMessage(content=system_prompt))

    for msg in messages:
        if "type" in msg:  
            if msg["type"] == "human":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["type"] == "ai":
                langchain_messages.append(AIMessage(content=msg["content"]))
            elif msg["type"] == "system":
                langchain_messages.append(SystemMessage(content=msg["content"]))
        else:  
            if msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))
            elif msg["role"] == "system":
                langchain_messages.append(SystemMessage(content=msg["content"]))

    config = {
        "configurable": {
            "thread_id": str(uuid.uuid4())
        }
    }

    assistant_message_id = f"msg-{uuid.uuid4().hex}"

    agent = await get_agent(system_prompt=system_prompt)
    async for chunk in agent.astream(
        {"messages": langchain_messages},
        config=config,
        stream_mode="messages"
    ):
        if isinstance(chunk, tuple) and len(chunk) >= 1:
            msg_chunk = chunk[0]
            if hasattr(msg_chunk, "content") and msg_chunk.content:
                chunk_data = {
                    "type": "ai",
                    "id": assistant_message_id,
                    "content": msg_chunk.content,
                }
                yield f"event: messages\ndata: {json.dumps([chunk_data])}\n\n"

    yield "event: end\ndata: null\n\n"

