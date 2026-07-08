from langgraph.graph import StateGraph, START, END
from agent.nodes.state import AgentState
from agent.nodes.problem_generation_node import generate_problem_node
from agent.nodes.testcase_generation_node import generate_testcases_node
from agent.nodes.reference_solver_node import generate_reference_solution_node
from agent.nodes.hint_generation_node import generate_hints_node
from agent.nodes.validation_node import validate_outputs_node
from agent.nodes.routing_node import route_next_action_node

def clean_state_node(state: AgentState) -> dict:
    """재생성 루프 진입 시 이전 시도의 데이터 오염을 예방하기 위해 상태를 클리닝하고,
    시도 횟수를 증가시킨다.
    """
    attempts = state.get("generation_attempts", 0) + 1
    
    # 이전 루프에서 생성된 더티 데이터 리셋
    return {
        "generation_attempts": attempts,
        "generated_problem": None,
        "testcase_bundle": None,
        "reference_solution": None,
        "validation_report": None,
        "hint_bundle": None,
        "routing_decision": None,
        "errors": []
    }

def route_validation(state: AgentState) -> str:
    """Validator의 검증 결과를 보고 다음 행동을 조건부 분기한다."""
    decision = state.get("routing_decision")
    attempts = state.get("generation_attempts", 1)
    
    if not decision:
        return "continue"
        
    # 검증 실패하여 재생성이 필요하고, 시도 횟수가 3회 미만인 경우 재생성 루프로 분기
    if decision.action == "regenerate_problem" and attempts < 3:
        return "regenerate"
        
    # 검증 통과(present_to_user) 또는 한도 도달 시 종료
    return "continue"

def build_graph():
    """문제 생성/검증 LangGraph StateGraph 조립"""
    workflow = StateGraph(AgentState)
    
    # 노드 등록
    workflow.add_node("clean_state", clean_state_node)
    workflow.add_node("problem_generation", generate_problem_node)
    workflow.add_node("testcase_generation", generate_testcases_node)
    workflow.add_node("reference_solution", generate_reference_solution_node)
    workflow.add_node("validation", validate_outputs_node)
    workflow.add_node("hint_generation", generate_hints_node)
    workflow.add_node("routing", route_next_action_node)
    
    # 기본 흐름 엣지 배선
    workflow.add_edge(START, "clean_state")
    workflow.add_edge("clean_state", "problem_generation")
    workflow.add_edge("problem_generation", "testcase_generation")
    workflow.add_edge("testcase_generation", "reference_solution")
    workflow.add_edge("reference_solution", "validation")
    
    # 조건부 엣지 배선 (Validation 검증 실패 시 재생성 루프)
    workflow.add_conditional_edges(
        "validation",
        route_validation,
        {
            "regenerate": "clean_state",
            "continue": "hint_generation"
        }
    )
    
    workflow.add_edge("hint_generation", "routing")
    workflow.add_edge("routing", END)
    
    return workflow.compile()
