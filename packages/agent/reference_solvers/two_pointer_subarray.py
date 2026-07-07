"""two_pointer_subarray 문제 유형의 결정론적 정답 코드 템플릿.

packages/agent/testcase_generators/two_pointer_subarray.py의
solve_two_pointer_subarray()와 동일한 로직을 독립 실행 가능한 Python 프로그램으로 옮긴 것이다.
"""

CODE = '''import sys


def solve_two_pointer_subarray(nums, k):
    left = 0
    current_sum = 0
    max_len = 0
    for right in range(len(nums)):
        current_sum += nums[right]
        while current_sum > k and left <= right:
            current_sum -= nums[left]
            left += 1
        if current_sum <= k:
            max_len = max(max_len, right - left + 1)
    return max_len


def main():
    lines = [line.strip() for line in sys.stdin.read().splitlines() if line.strip() != ""]
    _, k = map(int, lines[0].split())
    nums = list(map(int, lines[1].split()))
    print(solve_two_pointer_subarray(nums, k))


if __name__ == "__main__":
    main()
'''


def get_reference_solution_code() -> str:
    return CODE
