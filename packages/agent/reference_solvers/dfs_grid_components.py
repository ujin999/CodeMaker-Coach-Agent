"""dfs_grid_components 문제 유형의 결정론적 정답 코드 템플릿.

packages/agent/testcase_generators/dfs_grid_components.py의
solve_dfs_grid_components()와 동일한 로직을 독립 실행 가능한 Python 프로그램으로 옮긴 것이다.
"""

CODE = '''import sys


def solve_dfs_grid_components(grid):
    n = len(grid)
    m = len(grid[0])
    visited = [[False] * m for _ in range(n)]
    count = 0
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    for r in range(n):
        for c in range(m):
            if grid[r][c] == "1" and not visited[r][c]:
                count += 1
                stack = [(r, c)]
                visited[r][c] = True
                while stack:
                    cr, cc = stack.pop()
                    for dr, dc in dirs:
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < n and 0 <= nc < m:
                            if grid[nr][nc] == "1" and not visited[nr][nc]:
                                visited[nr][nc] = True
                                stack.append((nr, nc))
    return count


def main():
    lines = [line.strip() for line in sys.stdin.read().splitlines() if line.strip() != ""]
    n, m = map(int, lines[0].split())
    grid = lines[1:1 + n]
    print(solve_dfs_grid_components(grid))


if __name__ == "__main__":
    main()
'''


def get_reference_solution_code() -> str:
    return CODE
