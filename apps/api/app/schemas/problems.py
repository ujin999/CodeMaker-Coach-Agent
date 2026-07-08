from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field


class ProblemGenerateRequest(BaseModel):
    algorithm: str
    difficulty: str = "easy"
    problem_style: Optional[str] = None
    language: Optional[str] = "Python"
    learning_goal: Optional[str] = None
    user_level: Optional[str] = None
    recent_weaknesses: List[str] = Field(default_factory=list)
    recent_errors: List[str] = Field(default_factory=list)
    min_cases: int = 5
    allowed_hint_level: int = 3
    include_hints: bool = True
    seed: Optional[str] = None
    avoid_problem_ids: List[str] = Field(default_factory=list)
    force_new: bool = False
    focus_weaknesses: bool = True


class ProblemGenerateResponse(BaseModel):
    generated_problem: dict
    testcase_bundle: Optional[dict] = None
    hint_bundle: Optional[dict] = None
    reference_solution: Optional[dict] = None
    validation_report: Optional[dict] = None
    routing_decision: Optional[dict] = None
    gateway_mode: str = "unknown"
    generation_mode: Optional[str] = None
    seed: Optional[str] = None
    variant_id: Optional[str] = None

