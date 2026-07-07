"""budget_cap 문제 유형의 결정론적 정답 코드 템플릿.

packages/agent/testcase_generators/budget_cap.py의 solve_budget_cap()과
동일한 로직을 독립 실행 가능한 Python 프로그램으로 옮긴 것이다.
"""

CODE = '''import sys


def solve_budget_cap(requests, budget):
    if not requests:
        return 0
    low = 0
    high = max(requests)
    ans = 0
    while low <= high:
        mid = (low + high) // 2
        current_sum = sum(min(req, mid) for req in requests)
        if current_sum <= budget:
            ans = mid
            low = mid + 1
        else:
            high = mid - 1
    return ans


def main():
    lines = [line.strip() for line in sys.stdin.read().splitlines() if line.strip() != ""]
    requests = list(map(int, lines[1].split()))
    budget = int(lines[2])
    print(solve_budget_cap(requests, budget))


if __name__ == "__main__":
    main()
'''


def get_reference_solution_code() -> str:
    return CODE
