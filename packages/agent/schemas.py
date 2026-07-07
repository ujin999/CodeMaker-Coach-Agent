from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


class ProblemGenerationInput(BaseModel):
    """Input parameters for the problem generator."""
    algorithm: str = Field(description="The core algorithm type, e.g. binary_search, bfs, dfs, dp_basic, greedy")
    difficulty: str = Field(description="Target difficulty level, e.g. easy, medium, hard")
    problem_style: Optional[str] = Field(default=None, description="Style of the problem description, e.g. practical, mathematical")
    language: Optional[str] = Field(default=None, description="Target programming language, e.g. Python, Java, C++")
    learning_goal: Optional[str] = Field(default=None, description="Learning objective, e.g. parametric search, boundary conditions")
    user_level: Optional[str] = Field(default=None, description="Skill level of the user")
    recent_weaknesses: List[str] = Field(default_factory=list, description="List of user's recent weak concepts")


class HintBlueprint(BaseModel):
    """A blueprint mapping out the logical steps and constraints for hint generation."""
    intended_algorithm: List[str] = Field(description="Algorithm types needed to solve the problem")
    core_insight: str = Field(description="The main conceptual breakthrough needed")
    common_misconceptions: List[str] = Field(description="Common pitfalls or bugs to alert the user about")
    edge_case_focus: List[str] = Field(description="Extreme inputs or boundary values to check")
    forbidden_disclosures: List[str] = Field(description="Specific elements/code snippets that must not be revealed")
    level_1_guidance: str = Field(description="Strategic advice on direction without naming algorithm")
    level_2_guidance: str = Field(description="Algorithmic approach and conceptual outline")
    level_3_guidance: str = Field(description="Implementation check or structure explanation")
    allowed_code_exposure: Literal["none", "skeleton_only"] = Field(default="none")


class GeneratedProblem(BaseModel):
    """Structured output representation of a generated coding problem."""
    problem_id: str = Field(description="A unique identifier for the generated problem")
    title: str = Field(description="Problem title")
    difficulty: str = Field(description="Difficulty level")
    algorithm: List[str] = Field(description="Underlying algorithms")
    learning_goal: str = Field(description="Selected learning goal")
    statement: str = Field(description="The problem statement / story in detail")
    input_format: str = Field(description="Specification of input data format")
    output_format: str = Field(description="Specification of output data format")
    constraints: List[str] = Field(description="Input and execution constraints")
    sample_input: Optional[str] = Field(default=None, description="Example input data")
    sample_output: Optional[str] = Field(default=None, description="Expected output for sample input")
    expected_time_complexity: str = Field(description="Big-O complexity bound")
    hint_blueprint: HintBlueprint = Field(description="Blueprint containing prompt directions for staged hints")


class GeneratedTestcase(BaseModel):
    """Schema for individual generated testcase."""
    name: str = Field(description="Testcase name / label")
    input_data: str = Field(description="String input matching the input format")
    expected_output: str = Field(description="Expected output string")
    visibility: Literal["sample", "hidden", "edge"] = Field(description="Visibility category")
    purpose: str = Field(description="Explanation of what this case tests")
    difficulty_reason: Optional[str] = Field(default=None, description="Reason why this case is difficult")


class TestcaseBundle(BaseModel):
    """Schema representing the collection of testcases generated for a problem."""
    __test__ = False
    problem_id: str

    testcases: List[GeneratedTestcase]
    generation_notes: str

    @model_validator(mode="after")
    def validate_testcases(self) -> 'TestcaseBundle':
        has_sample = any(tc.visibility == "sample" for tc in self.testcases)
        if not has_sample:
            raise ValueError("TestcaseBundle must include at least one sample testcase")
        return self


class Hint(BaseModel):
    """Representing a staged hint that can be delivered to the user."""
    problem_id: str
    level: int = Field(description="Stage level of the hint: 1, 2, or 3")
    title: str = Field(description="A short title for the hint")
    content: str = Field(description="User-facing hint content")
    reveals_core_code: bool = Field(default=False)
    code_skeleton: Optional[str] = Field(default=None, description="Incomplete code template")
    concept_refs: List[str] = Field(default_factory=list, description="Related RAG concept filenames")
    source: str = Field(default="generated")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: int) -> int:
        if v not in [1, 2, 3]:
            raise ValueError("Hint level must be 1, 2, or 3")
        return v

    @field_validator("reveals_core_code")
    @classmethod
    def validate_reveals_core_code(cls, v: bool) -> bool:
        if v is not False:
            raise ValueError("reveals_core_code must always be False")
        return v

    @field_validator("content")
    @classmethod
    def validate_content_no_full_code(cls, v: str) -> str:
        # Check for full Python function implementation without placeholders
        if "def " in v and ":" in v and ("return" in v or "print" in v) and "TODO" not in v and "..." not in v and "pass" not in v:
            raise ValueError("Obvious full solution code detected in hint content.")
        
        # Check for full C++ main program
        if "#include" in v and "main(" in v and "TODO" not in v and "..." not in v:
            raise ValueError("Obvious full solution code detected in hint content.")
            
        return v

    @field_validator("code_skeleton")
    @classmethod
    def validate_skeleton_incomplete(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            # Check that code skeleton contains incomplete placeholders
            placeholders = ["...", "TODO", "pass", "here", "fill", "구현", "빈칸"]
            if not any(p in v.lower() for p in placeholders):
                raise ValueError("code_skeleton must be incomplete (include '...', 'TODO', or similar placeholders)")
        return v


class HintBundle(BaseModel):
    """Bundle of all hints (Level 1, 2, and 3) generated for a coding problem."""
    problem_id: str
    blueprint: HintBlueprint
    hints: List[Hint]
