CODE = '''import sys


def solve_lower_bound_count(array, x):
    if not array:
        return 0
    low = 0
    high = len(array) - 1
    ans = len(array)
    while low <= high:
        mid = (low + high) // 2
        if array[mid] >= x:
            ans = mid
            high = mid - 1
        else:
            low = mid + 1
    return ans


def main():
    lines = [line.strip() for line in sys.stdin.read().splitlines() if line.strip() != ""]
    if len(lines) < 2:
        return
    n, x = map(int, lines[0].split())
    array = list(map(int, lines[1].split()))
    print(solve_lower_bound_count(array, x))


if __name__ == "__main__":
    main()
'''


def get_reference_solution_code() -> str:
    return CODE
