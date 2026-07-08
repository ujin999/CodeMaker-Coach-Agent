CODE = '''import sys


def solve_immigration_time(times, m):
    if not times or m <= 0:
        return 0
    low = 1
    high = min(times) * m
    ans = high
    while low <= high:
        mid = (low + high) // 2
        people = sum(mid // t for t in times)
        if people >= m:
            ans = mid
            high = mid - 1
        else:
            low = mid + 1
    return ans


def main():
    lines = [line.strip() for line in sys.stdin.read().splitlines() if line.strip() != ""]
    if len(lines) < 2:
        return
    n, m = map(int, lines[0].split())
    times = list(map(int, lines[1].split()))
    print(solve_immigration_time(times, m))


if __name__ == "__main__":
    main()
'''


def get_reference_solution_code() -> str:
    return CODE
