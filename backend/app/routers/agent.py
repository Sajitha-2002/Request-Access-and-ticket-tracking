from fastapi import APIRouter, Depends
from ..schemas import AgentInput, AgentOutput
from ..auth import get_current_user
from ..models import User
from ..agents.langgraph_agent import run_agent

router = APIRouter(prefix="/api/agent", tags=["Agent"])


@router.post("/", response_model=AgentOutput)
def agent_endpoint(
    payload: AgentInput,
    current_user: User = Depends(get_current_user),
):
    result = run_agent(payload.message, payload.language)
    return AgentOutput(**result)
