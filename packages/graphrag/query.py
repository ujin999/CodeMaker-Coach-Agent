import logging
from packages.graphrag.driver import get_driver

logger = logging.getLogger(__name__)

def get_user_weaknesses(user_id: int) -> dict:
    """Queries Neo4j to retrieve the user's top weak concepts, error types, and custom recommendation details.
    
    Returns:
        dict: {
            "weak_concepts": [{"concept": "bfs", "score": 4.5}, ...],
            "top_errors": [{"error_type": "WA", "count": 3}, ...],
            "recommendation": "..."
        }
    """
    default_res = {
        "weak_concepts": [],
        "top_errors": [],
        "recommendation": "최근 진행된 평가 데이터가 없습니다. 계속 풀이에 도전하여 AI 추천 분석 리포트를 확인해 보세요!"
    }

    try:
        driver = get_driver()
    except Exception as e:
        logger.warning(f"Neo4j driver offline: {e}. Returning default user weaknesses.")
        return default_res

    weak_concepts = []
    top_errors = []

    with driver.session() as session:
        try:
            # 1. Fetch top 3 weak concepts
            concept_result = session.run(
                """
                MATCH (u:User {id: $user_id})-[r:WEAK_IN]->(c:Concept)
                WHERE r.weight_score > 0.0
                RETURN c.name AS concept, r.weight_score AS score
                ORDER BY score DESC, r.last_updated DESC
                LIMIT 3
                """,
                user_id=user_id,
            )
            for rec in concept_result:
                weak_concepts.append({
                    "concept": rec["concept"],
                    "score": round(float(rec["score"]), 2)
                })

            # 2. Fetch top 2 frequent error types
            error_result = session.run(
                """
                MATCH (u:User {id: $user_id})-[f:FAILED]->(p:Problem)-[:POTENTIAL_ERROR]->(e:ErrorType)
                RETURN e.name AS error_type, sum(f.count) AS err_count
                ORDER BY err_count DESC
                LIMIT 2
                """,
                user_id=user_id,
            )
            for rec in error_result:
                top_errors.append({
                    "error_type": rec["error_type"],
                    "count": int(rec["err_count"])
                })

        except Exception as e:
            logger.error(f"Failed to query user weaknesses from Neo4j: {e}")
            return default_res

    # 3. Generate personalized recommendation comment in Korean
    recommendation = ""
    if weak_concepts:
        primary_weakness = weak_concepts[0]["concept"]
        
        # Translate concept name to Korean for better UX
        korean_concepts = {
            "binary_search": "이분 탐색",
            "bfs": "너비 우선 탐색 (BFS)",
            "dfs": "깊이 우선 탐색 (DFS)",
            "two_pointer": "투 포인터",
            "dp_basic": "기초 동적 계획법 (DP)",
            "greedy": "그리디 알고리즘",
            "hash": "해시 (Hash Map)"
        }
        concept_ko = korean_concepts.get(primary_weakness, primary_weakness)
        
        error_ko = "논리적 계산"
        if top_errors:
            primary_error = top_errors[0]["error_type"]
            error_translations = {
                "WA": "틀린 답(Wrong Answer / 경계 조건 또는 설계 누수)",
                "TLE": "시간 초과(Time Limit Exceeded / 비효율적 반복문)",
                "RE": "런타임 에러(Runtime Error / 인덱스 범위 초과)",
                "MLE": "메모리 초과(Memory Limit Exceeded / 배열 과대 할당)"
            }
            error_ko = error_translations.get(primary_error, primary_error)

        recommendation = (
            f"AI 분석 결과, 현재 가장 많은 보완이 필요한 유형은 '{concept_ko}'이며, "
            f"주요 오답 요인은 '{error_ko}' 계통으로 진단되었습니다. "
            f"해당 유형의 문제를 한 번 더 생성하거나 쉬움/보통 단계 문제를 풀면서 기초 조작 범위 및 조건 흐름을 꼼꼼하게 다듬어 보세요!"
        )
    else:
        recommendation = "아주 훌륭합니다! 아직 특별한 취약 오답 개념이 검출되지 않았습니다. 난이도를 올려 새로운 유형의 문제 풀이에 끊임없이 도전해 보세요!"

    return {
        "weak_concepts": weak_concepts,
        "top_errors": top_errors,
        "recommendation": recommendation
    }
