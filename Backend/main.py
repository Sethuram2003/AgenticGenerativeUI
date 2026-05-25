import json
import os
import time
import uuid
from typing import Annotated, TypedDict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_BASE_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "minimax-m2.1:cloud")
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))

ollama_llm = ChatOllama(
    base_url=OLLAMA_BASE_URL,
    model=OLLAMA_MODEL,
    temperature=OLLAMA_TEMPERATURE,
)


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

class ChatRequest(BaseModel):
    messages: list[dict]
    systemPrompt: str | None = None

def _openai_chunk(delta: dict | None, finish_reason: str | None = None) -> bytes:
    payload = {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": OLLAMA_MODEL,
        "choices": [
            {
                "index": 0,
                "delta": delta or {},
                "finish_reason": finish_reason,
            }
        ],
    }
    return (json.dumps(payload) + "\n").encode("utf-8")


def _to_langchain_messages(messages: list[dict], system_prompt: str | None) -> list[BaseMessage]:
    output: list[BaseMessage] = []
    if system_prompt:
        output.append(SystemMessage(content=system_prompt))

    for message in messages:
        role = message.get("role")
        content = message.get("content", "")
        if role == "user":
            output.append(HumanMessage(content=content))
        elif role == "assistant":
            output.append(AIMessage(content=content))
        elif role == "system":
            output.append(SystemMessage(content=content))
    return output


def _build_graph() -> StateGraph:
    def run_model(state: ChatState) -> ChatState:
        response = ollama_llm.invoke(state["messages"])
        return {"messages": [response]}

    graph = StateGraph(ChatState)
    graph.add_node("model", run_model)
    graph.add_edge("model", END)
    graph.set_entry_point("model")
    return graph.compile()


chat_graph = _build_graph()


async def stream_langgraph_response(messages: list[dict], system_prompt: str | None):
    """Streams an OpenAI-compatible response using LangGraph + ChatOllama."""
    langchain_messages = _to_langchain_messages(messages, system_prompt)

    yield _openai_chunk({"role": "assistant"})
    async for chunk in ollama_llm.astream(langchain_messages):
        if isinstance(chunk, AIMessage) and chunk.content:
            yield _openai_chunk({"content": chunk.content})

    yield _openai_chunk({}, finish_reason="stop")


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Endpoint to stream OpenAI-compatible responses for OpenUI chat."""
    return StreamingResponse(
        stream_langgraph_response(request.messages, request.systemPrompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
        },
    )