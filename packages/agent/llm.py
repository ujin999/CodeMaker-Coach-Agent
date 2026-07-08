import os
from typing import Any, List, Optional, Type, Union, Literal
from pydantic import BaseModel
from config.settings import settings
from langchain_core.embeddings import Embeddings

# Try importing real providers
try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
except ImportError:
    ChatOpenAI = None
    OpenAIEmbeddings = None

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None


class FakeLocalEmbeddings(Embeddings):
    """Deterministic keyword-based fake embeddings model for offline testing."""
    
    KEYWORDS_MAP = {
        "binary_search": ["binary_search", "이분 탐색", "이진 탐색", "parametric search", "파라메트릭"],
        "bfs": ["bfs", "너비 우선"],
        "dfs": ["dfs", "깊이 우선", "백트래킹", "backtracking"],
        "dp_basic": ["dp_basic", "dp", "동적 계획", "dynamic programming"],
        "greedy": ["greedy", "탐욕", "그리디"],
        "hash": ["hash", "해시", "dictionary", "딕셔너리"],
        "two_pointer": ["two_pointer", "투 포인터", "two pointer"],
        "time_complexity": ["time_complexity", "시간 복잡도", "시간 초과", "tle", "big-o"],
        "off_by_one": ["off_by_one", "경계", "인덱스 오류"],
        "counter_example": ["counter_example", "반례"],
        "input_optimization": ["input_optimization", "가속", "sys.stdin"],
        "difficulty_template": ["difficulty_template", "난이도 템플릿"],
        "testcase_strategy": ["testcase_strategy", "테스트케이스 전략", "샘플 케이스"],
        "validator_checklist": ["validator_checklist", "검증 체크리스트"],
        "hint_policy": ["hint_policy", "힌트 정책"],
    }
    
    def _embed(self, text: str) -> List[float]:
        vector = [0.1] * 1536
        text_lower = text.lower()
        for idx, (stem, keywords) in enumerate(self.KEYWORDS_MAP.items()):
            if stem in text_lower or any(kw in text_lower for kw in keywords):
                vector[idx] = 100.0
        return vector

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)



class FakeStructuredChatModel:
    """Mock Chat Model that mimics LangChain models with `with_structured_output` support."""
    
    def __init__(self, responses: Optional[List[Any]] = None):
        self.responses = responses or []
        self.call_count = 0

    def with_structured_output(self, schema: Type[BaseModel], **kwargs: Any):
        parent_model = self
        
        class StructuredMock:
            def invoke(self, input: Any, *args: Any, **kwargs: Any) -> BaseModel:
                if parent_model.responses and parent_model.call_count < len(parent_model.responses):
                    res = parent_model.responses[parent_model.call_count]
                    parent_model.call_count += 1
                    if isinstance(res, schema):
                        return res
                    elif isinstance(res, dict):
                        return schema(**res)
                
                import inspect
                import re

                # Extract details from input messages
                msg_text = ""
                if isinstance(input, str):
                    msg_text = input
                elif isinstance(input, list):
                    msg_text = "\n".join(getattr(m, "content", "") for m in input)
                else:
                    msg_text = str(input)

                # Extract algorithm
                algo = "binary_search"
                algo_match = re.search(r"Core Algorithm:\s*(\S+)", msg_text)
                if algo_match:
                    algo = algo_match.group(1).strip().strip(",")
                
                # Extract seed
                seed = None
                seed_match = re.search(r"Generation Seed/Nonce:\s*(\S+)", msg_text)
                if seed_match:
                    seed = seed_match.group(1).strip()
                    if seed == "none" or not seed:
                        seed = None

                if schema.__name__ == "GeneratedProblem":
                    from agent.schemas import HintBlueprint
                    from agent.variants import select_variant

                    variant = select_variant(algo, seed)

                    p_id = f"stub-{algo}-001"
                    if seed:
                        clean_seed = "".join(c for c in seed if c.isalnum() or c == "_")[:8]
                        p_id = f"stub-{algo}_{clean_seed}-001"
                    
                    if variant:
                        tmpl = variant["stub_template"]
                        title = tmpl["title"]
                        if seed:
                            title += f" (Seed: {seed})"
                        statement = tmpl["statement"]
                        input_format = tmpl["input_format"]
                        output_format = tmpl["output_format"]
                        constraints = tmpl["constraints"]
                        sample_input = tmpl.get("sample_input")
                        sample_output = tmpl.get("sample_output")
                    else:
                        title = f"[STUB] {algo} 연습 문제"
                        if seed:
                            title += f" (Seed: {seed})"
                        statement = f"이 문제는 {algo} 알고리즘을 연습하기 위한 스터브 문제입니다. Seed: {seed or 'none'}"
                        if algo == "two_pointer":
                            statement += "\n투 포인터 sliding window로 합이 k 이하인 연속 부분 배열 최대 길이를 구합니다."
                        elif algo == "bfs":
                            statement += "\n격자에서 최단 거리를 BFS 너비 우선 탐색으로 구합니다. 상하좌우 벽"
                        elif algo == "dfs":
                            statement += "\n격자에서 연결 요소를 DFS 깊이 우선 탐색으로 구합니다. 상하좌우"
                        input_format = "입력 포맷"
                        output_format = "출력 포맷"
                        constraints = ["제한 사항"]
                        sample_input = None
                        sample_output = None

                    return schema(
                        problem_id=p_id,
                        title=title,
                        difficulty="easy",
                        algorithm=[algo],
                        learning_goal="기본 로직 이해",
                        statement=statement,
                        input_format=input_format,
                        output_format=output_format,
                        constraints=constraints,
                        sample_input=sample_input,
                        sample_output=sample_output,
                        expected_time_complexity="O(N)",
                        hint_blueprint=HintBlueprint(
                            intended_algorithm=[algo],
                            core_insight="핵심 통찰",
                            common_misconceptions=["실수"],
                            edge_case_focus=["경계값"],
                            forbidden_disclosures=["코드"],
                            level_1_guidance="1단계 가이드",
                            level_2_guidance="2단계 가이드",
                            level_3_guidance="3단계 가이드",
                        )
                    )

                # Fallback: construct dummy instance matching the schema fields
                import inspect
                
                def _create_dummy_data(sch: Type[BaseModel]) -> dict:
                    data = {}
                    for name, fd in sch.model_fields.items():
                        ann_type = fd.annotation
                        orig = getattr(ann_type, "__origin__", None)
                        
                        # Handle Optional/Union wrapper
                        if orig is Union:
                            union_args = getattr(ann_type, "__args__", [])
                            non_none = [a for a in union_args if a is not type(None)]
                            if non_none:
                                ann_type = non_none[0]
                                orig = getattr(ann_type, "__origin__", None)
                                
                        if inspect.isclass(ann_type) and issubclass(ann_type, BaseModel):
                            data[name] = ann_type(**_create_dummy_data(ann_type))
                        elif ann_type == str:
                            if "skeleton" in name.lower():
                                data[name] = f"mock_{name} # TODO: pass ..."
                            else:
                                data[name] = f"mock_{name}"
                        elif ann_type == int:
                            data[name] = 1
                        elif ann_type == float:
                            data[name] = 1.0
                        elif ann_type == bool:
                            data[name] = False
                        elif orig is list:
                            list_args = getattr(ann_type, "__args__", [])
                            if list_args and inspect.isclass(list_args[0]) and issubclass(list_args[0], BaseModel):
                                data[name] = [list_args[0](**_create_dummy_data(list_args[0]))]
                            else:
                                data[name] = []
                        elif orig is Literal:
                            lit_args = getattr(ann_type, "__args__", [])
                            data[name] = lit_args[0] if lit_args else None
                        else:
                            data[name] = None


                    return data
                    
                return schema(**_create_dummy_data(schema))
                
        return StructuredMock()



def _is_test_env() -> bool:
    return (
        os.getenv("ENV") == "test" or 
        os.getenv("USE_FAKE_EMBEDDINGS") == "true"
    )


def get_chat_model(provider: Optional[str] = None, model: Optional[str] = None, temperature: float = 0.0) -> Any:
    """Returns a LangChain ChatModel based on settings or falls back to fake model in test env."""
    if _is_test_env():
        return FakeStructuredChatModel()
        
    prov = provider or settings.llm_provider
    
    if prov == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is missing in settings.")
        if ChatOpenAI is None:
            raise ImportError("langchain-openai is not installed.")
        model_name = model or "gpt-4o-mini"
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=settings.openai_api_key,
        )
    elif prov == "claude" or prov == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is missing in settings.")
        if ChatAnthropic is None:
            raise ImportError("langchain-anthropic is not installed.")
        model_name = model or "claude-3-5-sonnet-latest"
        return ChatAnthropic(
            model=model_name,
            temperature=temperature,
            api_key=settings.anthropic_api_key,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {prov}")


def get_embedding_model() -> Any:
    """Returns an Embeddings client (OpenAIEmbeddings) or falls back to FakeLocalEmbeddings in test env."""
    if _is_test_env():
        return FakeLocalEmbeddings()
        
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is missing in settings for embeddings.")
        
    if OpenAIEmbeddings is None:
        raise ImportError("langchain-openai is not installed.")
        
    model_name = settings.embedding_model or "text-embedding-3-small"
    return OpenAIEmbeddings(
        model=model_name,
        api_key=settings.openai_api_key,
    )

