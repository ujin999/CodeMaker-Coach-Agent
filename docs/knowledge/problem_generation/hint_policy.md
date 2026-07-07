# Hint Policy (힌트 정책 및 가이드라인)

- **Korean Keywords**: 힌트 정책, 단계별 힌트, 힌트 수위 제어, 정답 유출 방지, 스켈레톤 코드
- **English Keywords**: Hint Policy, Level-staged Hint, Code Exposure Filter, Skeleton Code, Hint Security

## Concept Summary
CodeMaker Coach Agent의 핵심 교육 원칙으로, 학습자가 문제 해결 도중 정답을 통째로 카피해 제출하는 단순 풀이 방식에서 벗어나, 점진적인 논리 유도를 통해 스스로 해결하게 만드는 보안 및 수위 필터 규정입니다.

## Staged Hint Levels
- **1단계 (Level 1) - 접근 방향 (Directional Hint)**:
  - 직접적인 알고리즘 기법 이름(예: "이분 탐색을 쓰세요")은 최대한 언급하지 않습니다.
  - 대신 "데이터의 크기가 매우 크고 조건에 따라 구간을 반씩 좁혀나갈 수 있는지 고민해 보세요"와 같이 문제를 관찰하는 눈을 기르게 돕습니다.
- **2단계 (Level 2) - 구체적인 해결 전략 (Algorithmic Strategy)**:
  - 필요한 알고리즘 개념과 핵심 아이디어를 제시합니다 (예: "매개 변수 탐색을 적용하여 기준 값을 만족하는 최대 길이를 찾으세요").
  - 시간 복잡도를 줄일 수 있는 구체적인 가이드나 활용할 자료구조를 언급합니다.
- **3단계 (Level 3) - 세부 구현 포인트 및 스켈레톤 (Implementation Details)**:
  - 반복 조건의 임계값 계산, 오차 처리, 혹은 필요한 자료구조 선언과 뼈대 코드(Skeleton Code) 수준만 제시합니다.
  - **절대로 정답이 되는 핵심 논리 코드(Acceptable Solution)를 완전 노출해서는 안 됩니다.**

## Security and Filtering Rules
1. **정답 차단**: 모든 힌트 응답의 `reveals_core_code` 속성은 반드시 `False`여야 하며, 전체 솔루션은 비공개로 유지되어야 합니다.
2. **사전 생성 및 물리적 차단**: 힌트는 런타임에 LLM이 즉석 생성하는 것을 배제하고 문제 생성 시점에 미리 구조를 짜두어 DB에 두고 서빙하며, 검색 쿼리단에서 현재 `allowed_level` 이상의 힌트는 데이터베이스/벡터스토어 수준에서 제외하여 프롬프트 인젝션 우려를 원천 봉쇄합니다.
