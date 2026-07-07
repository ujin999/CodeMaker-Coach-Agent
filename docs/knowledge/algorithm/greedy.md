# Greedy (탐욕법)

- **Korean Keywords**: 탐욕법, 그리디, 정렬, 최적화 선택, 국소적 최적해
- **English Keywords**: Greedy Algorithm, Sorting, Locally Optimal Choice, Fractional Knapsack, Activity Selection

## Concept Summary
그리디 알고리즘은 매 단계마다 지금 당장 보기에 가장 최선이라고 판단되는 최적의 선택(Locally Optimal Choice)을 해나가면서 최종적으로 전체 문제의 해답에 도달하는 기법입니다.

## When to Use
- 매 순간의 부분적인 최적 선택이 모여 전체의 최적해를 구성할 때 (Greedy Choice Property).
- 다른 완전 탐색이나 DP 방식보다 압도적으로 빠르게 해결하는 직관적 규칙이 존재하며 증명 가능할 때.
- 보통 정렬(Sorting)이나 우선순위 큐(Priority Queue)와 결합되는 경우가 많습니다.

## Common Mistakes
- 매 순간의 최적 선택이 전체의 전역적 최적화(Globally Optimal Solution)를 보장하지 못함에도 잘못 그리디 접근을 정당화하여 오답을 내는 경우.
- 정렬 기준(예: 회의실 배정에서 시작 시간 기준 정렬 vs 종료 시간 기준 정렬)의 오류.

## Time Complexity Guidance
- 일반적으로 정렬 작업이 지배적이며 $O(N \log N)$ 내외로 해결 가능.
- 순차 스캔이나 힙(Heap) 갱신은 $O(N)$ 또는 $O(N \log K)$ 소요.

## Problem Generation Guidance
- 동전 거스름돈 최소화, 회의실 배정 문제, 스케줄링 최소화 등 전형적인 그리디 응용 형식을 취하십시오.
- 그리디 알고리즘의 핵심 규칙(예: 정렬 기준)을 유추하기 위해 예시 시나리오가 일관되게 맞아떨어지도록 설명해야 합니다.

## Testcase Generation Guidance
- 단순히 앞의 큰 값만 골라갔을 때 실패하는 반례적 패턴의 반례 테스트케이스를 숨겨둔 테스트케이스로 구성하십시오.
- 입력 크기 및 원소값들의 정렬 순서가 완전 역순이거나 이미 정렬된 형태 등의 변이형을 설계하십시오.

## Hint Guidance
- 1단계: 모든 대안을 다 보기 전에 매 단계에서 당장 가장 큰 이득을 주는 요소를 기준으로 정렬하고 접근(그리디)할 수 있을지 고려합니다.
- 2단계: 최적의 조합 규칙을 정렬 기준(예: 종료 시간 순, 무게 대비 가치 순 등)으로 설정할 수 있는지 확인해 보라고 조언합니다.
- 3단계: 정렬 후에 루프를 돌며 기준에 맞는 항목을 우선순위 있게 선택하고 필터링해 나가는 스켈레톤 아이디어를 제시합니다.
