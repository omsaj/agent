"""FastAPI API for interacting with the :class:`LocalAgent`."""

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

from agent.core import LocalAgent


# Reuse a single agent instance for all requests
agent = LocalAgent()

router = APIRouter()


class ChatRequest(BaseModel):
    """Request body for the ``/chat`` endpoint."""

    text: str


class ToolRequest(BaseModel):
    """Request body for the ``/tool`` endpoint."""

    name: str
    input: str


@router.post("/chat")
async def chat(req: ChatRequest) -> str:
    """Return the agent's response for the given text."""

    return agent.process_input(req.text)


@router.post("/tool")
async def tool(req: ToolRequest) -> str:
    """Execute a named tool with the provided input."""

    return agent.run_tool(req.name, req.input)


app = FastAPI()
app.include_router(router)


@app.get("/")
async def root() -> dict[str, str]:
    """Health check endpoint."""

    return {"status": "ok"}
