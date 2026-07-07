# Binary Search (이분 탐색)

- **Korean Keywords**: 이분 탐색, 이진 탐색, 매개 변수 탐색, 파라메트릭 서치, 경계값 결정
- **English Keywords**: Binary Search, Parametric Search, Lower Bound, Upper Bound, Boundary Search

## Concept Summary
이분 탐색은 정렬된 배열 또는 결정 가능한 단조 함수 공간에서 탐색 범위를 반씩 줄여가며 원하는 값의 위치나 조건을 만족하는 최적의 값을 찾는 알고리즘입니다.

## When to Use
- 탐색 범위가 매우 크고 ($N \ge 10^7$), 탐색 대상 리스트가 정렬되어 있을 때.
- 최적화 문제를 결정 문제(Yes/No)로 바꾸어 푸는 Parametric Search가 적용 가능할 때.

## Common Mistakes
- 탐색 공간이 정렬되어 있지 않은 상태에서 이분 탐색을 수행하는 경우.
- 인덱스 갱신 시 `mid - 1` 또는 `mid + 1` 처리를 빠뜨려 무한 루프에 빠지는 경우.
- `low + high` 계산 시 정수 오버플로우가 발생하는 경우.
- 최적해 경계 조건(Lower bound / Upper bound) 처리의 미숙.

## Time Complexity Guidance
- $O(\log N)$ 탐색 보장.
- 결정 문제의 시간 복잡도가 $O(C)$인 경우, Parametric Search는 $O(C \log N)$ 소요.

## Problem Generation Guidance
- 문제 상황은 정렬 상태를 암시하거나 탐색 공간이 매우 넓은 조건이어야 합니다.
- 단순 인덱스 매칭이 아니라 실생활 응용 문제(예: 특정 예산 범위 내 최대 효율 등)를 출제하십시오.

## Testcase Generation Guidance
- 배열의 최소/최대 길이 케이스, 경계 값 케이스(답이 맨 처음이거나 맨 끝인 경우)를 반드시 포함하십시오.
- 타겟 값이 배열에 없는 경우의 에지 케이스를 포함하십시오.

## Hint Guidance
- 1단계: 탐색 범위가 매우 크다는 점과 탐색 대상이 정렬될 수 있는지 확인해보라고 안내합니다.
- 2단계: 최댓값의 최솟값 또는 최솟값의 최댓값을 구하는 결정 문제(Parametric Search)로 변환해보라고 제안합니다.
- 3단계: mid를 갱신하는 조건 및 mid 값을 조건 함수에 대입하여 범위를 좁히는 뼈대 인덱스 연산 구조를 설명합니다.
