CODE = '''import sys


def solve_cable_cutting(lengths, k):
    if not lengths or k <= 0:
        return 0
    low = 1
    high = max(lengths)
    ans = 0
    while low <= high:
        mid = (low + high) // 2
        pieces = sum(l // mid for l in lengths)
        if pieces >= k:
            ans = mid
            low = mid + 1
        else:
            high = mid - 1
    return ans


def main():
    lines = [line.strip() for line in sys.stdin.read().splitlines() if line.strip() != ""]
    if len(lines) < 2:
        return
    n, k = map(int, lines[0].split())
    lengths = list(map(int, lines[1].split()))
    print(solve_cable_cutting(lengths, k))


if __name__ == "__main__":
    main()
'''


def get_reference_solution_code() -> str:
    return CODE
