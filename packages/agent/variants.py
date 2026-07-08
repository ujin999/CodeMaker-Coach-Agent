import hashlib

VARIANTS = {
    "binary_search": [
        {
            "variant_id": "budget_cap",
            "required_keywords": ["예산", "상한", "배정", "cap", "budget"],
            "forbidden_keywords": ["랜선", "자르기", "케이블", "나무", "공유기", "설치", "거리", "심사", "입국", "시간", "정렬", "첫 번째", "인덱스"],
            "prompt_instruction": (
                "The problem must be formulated as a budget cap problem: finding the maximum integer C (상한액) "
                "such that the sum of min(request_i, C) is less than or equal to a total budget B. "
                "You MUST explicitly include the exact phrases: '상한액 C', 'min(요청 예산, C)', and 'sum(min(request_i, C)) <= B'."
            ),
            "stub_template": {
                "title": "예산 상한액 찾기",
                "statement": "여러 지방자치단체의 요청 예산과 총 예산 B가 주어질 때, 정부의 예산 배정 상한액 C의 최댓값을 구하시오. 배정 방식은 min(요청 예산, C)이며, 배정액 총합은 B 이하(sum(min(request_i, C)) <= B)여야 합니다.",
                "input_format": "첫째 줄에 지방자치단체의 수 N이 주어집니다.\n둘째 줄에 각 요청 예산이 공백으로 구분되어 주어집니다.\n셋째 줄에 총 예산 B가 주어집니다.",
                "output_format": "배정 가능한 최대 상한액 C를 출력합니다.",
                "constraints": ["1 <= N <= 10,000", "1 <= 요청 예산 <= 100,000", "N <= B <= 1,000,000,000"],
                "sample_input": "4\n120 110 140 150\n485",
                "sample_output": "127",
            }
        },
        {
            "variant_id": "cable_cutting",
            "required_keywords": ["랜선", "자르기", "케이블", "나무"],
            "forbidden_keywords": ["상한액", "배정", "공유기", "설치", "거리", "심사", "입국", "시간", "정렬", "첫 번째", "인덱스"],
            "prompt_instruction": (
                "The problem must be formulated as a cable/log cutting problem: cutting N cables/logs of different lengths "
                "to produce at least K pieces of equal length. Find the maximum possible integer length of the cut pieces. "
                "You MUST explicitly include the exact phrases: '랜선', '자르기', '개수 K', and '최대 길이'."
            ),
            "stub_template": {
                "title": "랜선 자르기",
                "statement": "길이가 제각각인 N개의 랜선이 있습니다. 이를 동일한 길이로 잘라서 최소 K개의 랜선을 만들려고 합니다. 만들 수 있는 랜선의 최대 길이를 구하시오. 잘라내고 남은 랜선은 버립니다.",
                "input_format": "첫째 줄에 이미 가지고 있는 랜선의 개수 N과 필요한 랜선의 개수 K가 공백으로 구분되어 주어집니다.\n둘째 줄에 N개 랜선의 각 길이가 공백으로 구분되어 주어집니다.",
                "output_format": "만들 수 있는 랜선의 최대 길이를 출력합니다.",
                "constraints": ["1 <= N <= 10,000", "1 <= K <= 1,000,000", "N <= K", "각 랜선의 길이는 1 이상 2^31-1 이하"],
                "sample_input": "4 11\n802 743 457 539",
                "sample_output": "200",
            }
        },
        {
            "variant_id": "router_installation",
            "required_keywords": ["공유기", "설치", "거리"],
            "forbidden_keywords": ["상한액", "배정", "랜선", "자르기", "케이블", "나무", "심사", "입국", "시간", "정렬", "첫 번째", "인덱스"],
            "prompt_instruction": (
                "The problem must be formulated as a router installation problem: placing C routers on N coordinate houses "
                "to maximize the minimum distance between any two adjacent routers. "
                "You MUST explicitly include the exact phrases: '공유기', '설치', '최대 거리', and '최소 거리'."
            ),
            "stub_template": {
                "title": "공유기 설치",
                "statement": "N개의 집이 수직선 상에 위치해 있습니다. 이 중 C개의 집에 공유기를 설치하려고 합니다. 한 집에는 공유기를 최대 하나만 설치할 수 있고, 가장 인접한 두 공유기 사이의 거리를 최대로 하고자 합니다. 이때의 최대 최소 거리를 구하시오.",
                "input_format": "첫째 줄에 집의 개수 N과 공유기의 개수 C가 공백으로 구분되어 주어집니다.\n둘째 줄에 집들의 좌표가 공백으로 구분되어 주어집니다.",
                "output_format": "가장 인접한 두 공유기 사이의 최대 거리를 출력합니다.",
                "constraints": ["2 <= N <= 200,000", "2 <= C <= N", "집의 좌표는 0 이상 1,000,000,000 이하인 정수"],
                "sample_input": "5 3\n1 2 8 4 9",
                "sample_output": "3",
            }
        },
        {
            "variant_id": "immigration_time",
            "required_keywords": ["심사", "입국심사", "시간"],
            "forbidden_keywords": ["상한액", "배정", "랜선", "자르기", "케이블", "나무", "공유기", "설치", "거리", "정렬", "첫 번째", "인덱스"],
            "prompt_instruction": (
                "The problem must be formulated as an immigration booth processing time problem: finding the minimum time "
                "required to process M people with N immigration counters, where each counter takes a different amount of time. "
                "You MUST explicitly include the exact phrases: '심사', '입국심사', and '최소 시간'."
            ),
            "stub_template": {
                "title": "입국심사",
                "statement": "N개의 입국심사대에서 심사관들이 한 사람을 심사하는 데 걸리는 시간이 다릅니다. 심사를 기다리는 사람이 M명일 때, 모든 사람이 심사를 받는 데 걸리는 최소 시간을 구하시오.",
                "input_format": "첫째 줄에 심사대의 개수 N과 대기자 수 M이 공백으로 구분되어 주어집니다.\n둘째 줄에 각 심사대별로 심사에 걸리는 시간이 공백으로 구분되어 주어집니다.",
                "output_format": "모든 사람이 심사를 마칠 수 있는 최소 시간을 출력합니다.",
                "constraints": ["1 <= N <= 100,000", "1 <= M <= 1,000,000,000", "각 심사대별 소요 시간은 1 이상 1,000,000,000 이하"],
                "sample_input": "2 6\n7 10",
                "sample_output": "28",
            }
        },
        {
            "variant_id": "lower_bound_count",
            "required_keywords": ["첫 번째", "인덱스", "이상", "정렬"],
            "forbidden_keywords": ["상한액", "배정", "랜선", "자르기", "케이블", "나무", "공유기", "설치", "거리", "심사", "입국"],
            "prompt_instruction": (
                "The problem must be formulated as a lower bound search: finding the first index (0-indexed) in a sorted array "
                "of N elements where the value is greater than or equal to a target value X. If all elements are smaller than X, return N. "
                "You MUST explicitly include the exact phrases: '정렬', '첫 번째', '이상', and '인덱스'."
            ),
            "stub_template": {
                "title": "정렬된 배열에서 값 찾기",
                "statement": "오름차순으로 정렬된 N개의 정수로 이루어진 배열이 주어집니다. 이 배열에서 특정 값 X 이상인 원소가 처음으로 나타나는 인덱스를 구하시오. 만약 모든 원소가 X 미만이라면 N을 출력합니다.",
                "input_format": "첫째 줄에 배열의 크기 N과 목표 값 X가 공백으로 구분되어 주어집니다.\n둘째 줄에 오름차순 정렬된 N개의 정수가 공백으로 구분되어 주어집니다.",
                "output_format": "조건을 만족하는 첫 번째 원소의 0-based 인덱스를 출력합니다.",
                "constraints": ["1 <= N <= 1,000,000", "-1,000,000,000 <= X <= 1,000,000,000", "배열의 원소는 -1,000,000,000 이상 1,000,000,000 이하 정수"],
                "sample_input": "5 3\n1 3 3 5 7",
                "sample_output": "1",
            }
        }
    ]
}

def select_variant(algorithm: str, seed: str | None) -> dict | None:
    if algorithm not in VARIANTS:
        return None
    variants = VARIANTS[algorithm]
    if not seed:
        return variants[0]
    
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    idx = int(h, 16) % len(variants)
    return variants[idx]
