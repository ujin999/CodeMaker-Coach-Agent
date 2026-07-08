CODE = '''import sys


def solve_router_installation(coords, c):
    if not coords or c < 2:
        return 0
    coords = sorted(coords)
    low = 1
    high = coords[-1] - coords[0]
    ans = 0
    while low <= high:
        mid = (low + high) // 2
        count = 1
        last = coords[0]
        for i in range(1, len(coords)):
            if coords[i] - last >= mid:
                count += 1
                last = coords[i]
        if count >= c:
            ans = mid
            low = mid + 1
        else:
            high = mid - 1
    return ans


def main():
    lines = [line.strip() for line in sys.stdin.read().splitlines() if line.strip() != ""]
    if len(lines) < 2:
        return
    n, c = map(int, lines[0].split())
    coords = list(map(int, lines[1].split()))
    print(solve_router_installation(coords, c))


if __name__ == "__main__":
    main()
'''


def get_reference_solution_code() -> str:
    return CODE
