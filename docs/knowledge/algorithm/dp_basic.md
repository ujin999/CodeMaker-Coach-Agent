# Dynamic Programming Basic (기초 동적 계획법)

- **Korean Keywords**: 동적 계획법, 다이나믹 프로그래밍, 점화식, 메모이제이션, 탑다운, 바텀업
- **English Keywords**: Dynamic Programming, Memoization, Overlapping Subproblems, Optimal Substructure, DP Table

## Concept Summary
동적 계획법(DP)은 큰 문제를 여러 개의 작은 하위 문제로 나누고, 하위 문제의 정답을 메모리(DP Table)에 저장(Memoization)하여 중복 연산을 피해 전체 문제의 최적해를 효율적으로 도출하는 방법입니다.

## When to Use
- 하위 문제들의 계산결과가 계속 반복되어 나타날 때 (Overlapping Subproblems).
- 전체 문제의 최적의 해가 부분 문제들의 최적의 해들로부터 조합될 때 (Optimal Substructure).

## Common Mistakes
- 점화식의 베이스 케이스(초기 값, e.g. DP[0], DP[1])를 올바르게 정의하지 않아 인덱스 에러나 오답이 발생하는 경우.
- 중복 연산에 대한 메모이제이션 처리가 누락되어 단순 재귀와 동일하게 시간 초과를 겪는 경우.
- 점화식 관계(상태 전이)의 선후 관계 설정을 잘못하여 이전 루프 결과가 다음 루프에 오염되는 경우.

## Time Complexity Guidance
- 상태의 개수 $\times$ 한 상태에서의 전이 연산 시간.
- 일반적으로 부분 문제 개수가 $N$이고 전이에 상수 시간이 걸리면 $O(N)$에 해결 가능.

## Problem Generation Guidance
- 계단 오르기, 배낭 문제 변형, 최댓값/최솟값 누적 합 등의 템플릿을 고려하십시오.
- 상태의 정의(DP 배열의 인덱스 의미)와 값의 전이(점화식)가 명확하고 납득 가능한 범위에서 설계되도록 유도합니다.

## Testcase Generation Guidance
- 수열의 길이 $N$이 최소인 경우($N=1, 2$)의 경계값을 테스트에 포함시켜 Out of Bounds 에러를 잡으십시오.
- 큰 입력값 조건에서 오버플로우가 날 수 있는 자료형 처리 검증용 케이스를 포함하십시오.

## Hint Guidance
- 1단계: 중복 계산이 빈번하게 일어나는 하위 문제들을 메모리에 기록하여 재사용하는 동적 계획법(DP)이 적용되는지 검토합니다.
- 2단계: 최적해의 구조적 전이를 찾아보고 `dp[i]`가 의미하는 바가 무엇인지 구체적으로 정의하며 점화식을 유도해 보라고 조언합니다.
- 3단계: 점화식을 바탕으로 초기 배열 값(베이스 케이스) 설정 및 반복문을 통해 누적 계산을 완성하는 뼈대 코드를 보여줍니다.
