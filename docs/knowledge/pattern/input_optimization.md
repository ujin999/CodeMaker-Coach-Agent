# Input Optimization (입출력 가속 및 최적화 패턴)

- **Korean Keywords**: 입출력 속도, 입출력 가속, 가비지 컬렉션, 시간 초과 방지
- **English Keywords**: Fast I/O, Input Optimization, sys.stdin.readline, Timeout Prevention, Python Performance

## Concept Summary
Python 등 비교적 인터프리터 속도가 느린 언어로 작성된 프로그램이 수십만 개에 달하는 많은 줄의 입력값 데이터를 읽어들일 때, 표준 `input()` 함수가 유발하는 입출력 병목 현상으로 인해 발생하는 불필요한 시간 초과(TLE)를 극복하기 위한 최적화 기법입니다.

## When to Use
- 로직 자체의 시간 복잡도는 문제가 없으나(예: $O(N)$), 데이터 입력 건수 $N \ge 100,000$ 일 때 입출력 병목으로 인해 시간 초과가 뜰 때.
- 채점 결과가 로컬에서는 잘 도는데 서버 환경에서만 TLE가 뜨며, 입력양이 비정상적으로 많을 때 적용합니다.

## Language-Specific Accelerations
- **Python**:
  ```python
  import sys
  input = sys.stdin.readline
  ```
  - 개행 문자(`\n`)가 포함되므로 `strip()` 이나 `split()` 과 함께 사용하는 경우가 많습니다.
- **Java**: `Scanner` 대신 `BufferedReader`와 `StringTokenizer` 사용.
- **C++**: `cin.tie(NULL); ios_base::sync_with_stdio(false);` 적용.

## Common Mistakes
- `sys.stdin.readline`을 문자열 그대로 읽을 때 개행 문자(`\n`) 처리를 하지 않아 논리 조건문에서 불일치가 일어나는 경우.
- 입출력 양이 수십 개 수준으로 극히 적은 데도 복잡하게 입출력 가속만 찾아다니며 진짜 알고리즘의 비효율성을 방치하는 경우.

## Problem/Hint Guidance
- 대용량 입력이 강제되는 문제(예: 정렬, 해시 조회, 구간 합)에서는 설명이나 힌트에 반드시 입출력 속도 가속화 기법 사용에 대한 주의사항을 일러주어야 합니다.
