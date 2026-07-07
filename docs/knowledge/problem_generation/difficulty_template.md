# Problem Generation Difficulty Templates (난이도별 문제 생성 템플릿)

- **Korean Keywords**: 난이도 템플릿, 실버, 골드, 제한조건 설정, 알고리즘 난이도
- **English Keywords**: Difficulty Level, Solver Level, Constraint Settings, Problem Template

## Concept Summary
생성되는 문제의 체감 난이도를 결정하는 기준표입니다. 사용자가 선택한 난이도(하/중/상 또는 백준 실버/골드 기준)에 맞게 입력 제약, 상황 복잡도, 그리고 예외 상황의 수를 통제하여 적절한 수준의 코딩 테스트 문제를 일관성 있게 생산합니다.

## Difficulty Levels Mapping and Constraints
- **쉬움 (Easy) / 실버 레벨**:
  - 기본 데이터 크기 $N \le 1,000$.
  - 1차원 배열, 간단한 탐색(DFS/BFS), 단방향 그리디, 기초 해시 매핑.
  - 특별한 가속화나 심오한 예외 처리 요구를 최소화하고 기본 로직 구현에 초점을 둡니다.
- **보통 (Medium) / 실버 상위~골드 하위 레벨**:
  - 데이터 크기 $N \le 100,000$.
  - 최적화 시간 복잡도를 요구하는 이분 탐색, 구간 갱신(투 포인터/슬라이딩 윈도우), 정렬이 결합된 그리디, 기초 동적계획법.
  - 에지 케이스(중복값, 0, 빈 값 등)에 대한 예외 분기를 1~2개 필수 포함합니다.
- **어려움 (Hard) / 골드 중위~골드 상위 레벨**:
  - 데이터 크기 $N \ge 200,000$ 또는 복합 다차원 탐색.
  - 최단 경로 결합 그래프 연산, 메모이제이션 차원이 3개 이상인 DP, 복합 자료구조 혼합(Priority Queue + Hash Map 등).
  - 다차원 경계 영역 예외 및 극도의 메모리/시간 최적화(Fast I/O 등)를 반드시 요구합니다.

## Problem Generation Guidance
- 사용자가 "Easy"를 골랐는데 $O(N \log N)$ 알고리즘을 꽉 채운 십만 개 배열을 강제하지 마십시오.
- 반대로 "Hard"를 골랐는데 단순 이중 포문으로 다 풀리는 단방향 탐색은 피하십시오. 반드시 RAG 개념을 적용해 적정 제약을 잡으십시오.
