# packages/rag — RAG 파이프라인

`docs/knowledge/`의 알고리즘 개념 문서 및 문제별 생성된 힌트를 색인하고 검색하는 패키지입니다.

## 핵심 기능

1. **Concept RAG**:
   - `docs/knowledge/` 디렉터리에 있는 마크다운 문서를 읽어들여 텍스트 청크로 쪼개고 색인합니다.
   - 문제 생성, 테스트케이스 생성, 힌트 생성 시점에 관련 개념과 문제 해결 가이드라인을 제공합니다.
   
2. **Hint RAG**:
   - 문제 생성 시 함께 저장되는 1~3단계 힌트 묶음을 개별 문제별로 조회 가능하게 색인합니다.
   - 챗봇 형식의 풀이 지원 화면에서 사용됩니다.

## 보안 및 필터링 정책 (allowed_level filtering)

- **물리적 Retrieval-level 필터링**:
  사용자가 챗봇을 통해 힌트를 요청할 때, 서버는 사용자 세션에서 확인된 `allowed_level` 이상의 힌트를 **검색 결과(Retriever)단에서 필터링하여 완전히 제거**합니다.
- 단순히 LLM 프롬프트에 "allowed_level 이상의 힌트는 보여주지 마"라고 지시하는 방식(Prompt-only filtering)은 프롬프트 인젝션에 취약하므로, 검색 단계에서 물리적으로 상위 레벨 힌트를 원천 배제합니다.
- `reveals_core_code == True` 인 힌트 또한 보안 검증을 거쳐 검색 결과에서 즉각 탈락시킵니다.

## 저장소 지원 (Qdrant 및 로컬 Fallback)

- **Qdrant**: `docker-compose` 환경의 Qdrant 서버를 활용하여 벡터 컬렉션(`codemaker_concepts`, `codemaker_hints`)을 운용합니다.
- **In-Memory Fallback**: 로컬 테스트 환경이나 Qdrant 인프라가 미작동할 경우, 자동으로 `InMemoryVectorStore`로 전환되어 외부 서버 의존성 없이 로직 및 유닛 테스트가 완벽히 통과하도록 설계되어 있습니다.
