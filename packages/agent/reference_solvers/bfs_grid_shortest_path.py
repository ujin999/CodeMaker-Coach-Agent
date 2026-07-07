"""bfs_grid_shortest_path 문제 유형의 결정론적 정답 코드 템플릿.

packages/agent/testcase_generators/bfs_grid_shortest_path.py의
solve_bfs_grid_shortest_path()와 동일한 로직을 독립 실행 가능한 Python 프로그램으로 옮긴 것이다.
"""

CODE = '''import sys
from collections import deque


def solve_bfs_grid_shortest_path(grid):
    n = len(grid)
    m = len(grid[0])

    if grid[0][0] == "1" or grid[n - 1][m - 1] == "1":
        return -1
    if n == 1 and m == 1:
        return 1

    visited = [[False] * m for _ in range(n)]
    queue = deque([(0, 0, 1)])
    visited[0][0] = True
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    while queue:
        r, c, d = queue.popleft()
        if r == n - 1 and c == m - 1:
            return d
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < n and 0 <= nc < m:
                if grid[nr][nc] == "0" and not visited[nr][nc]:
                    visited[nr][nc] = True
                    queue.append((nr, nc, d + 1))
    return -1


def main():
    lines = [line.strip() for line in sys.stdin.read().splitlines() if line.strip() != ""]
    n, m = map(int, lines[0].split())
    grid = lines[1:1 + n]
    print(solve_bfs_grid_shortest_path(grid))


if __name__ == "__main__":
    main()
'''


def get_reference_solution_code() -> str:
    return CODE
