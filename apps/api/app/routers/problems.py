from __future__ import annotations
from fastapi import APIRouter, Depends
from app.gateway import AgentGateway, get_agent_gateway
from app.schemas.problems import ProblemGenerateRequest, ProblemGenerateResponse

router = APIRouter(prefix="/api/problems", tags=["problems"])


@router.post("/generate", response_model=ProblemGenerateResponse)
async def generate_problem(
    request: ProblemGenerateRequest,
    gateway: AgentGateway = Depends(get_agent_gateway)
) -> ProblemGenerateResponse:
    """
    Generate a coding problem, build testcases, validate, and route.
    """
    return await gateway.generate_problem_package(request)
