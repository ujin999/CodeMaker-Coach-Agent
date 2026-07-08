import logging
from datetime import datetime
from packages.graphrag.driver import get_driver

logger = logging.getLogger(__name__)

def record_submission_to_graph(
    user_id: int,
    user_email: str,
    problem_id: str,
    problem_title: str,
    problem_difficulty: str,
    problem_algorithms: list[str],
    status: str,
) -> None:
    """Synchronizes coding test submission results to Neo4j Graph Database.
    Updates weakness weights and creates SOLVED/FAILED relationships.
    """
    try:
        driver = get_driver()
    except Exception as e:
        logger.warning(f"Skipping graph sync because Neo4j driver is not available: {e}")
        return

    now_iso = datetime.utcnow().isoformat()

    # Normalize difficulty
    diff = problem_difficulty.lower()
    if diff not in ["easy", "medium", "hard"]:
        diff = "medium"

    with driver.session() as session:
        try:
            # 1. Merge User and Problem nodes, link Problem to its concepts
            session.run(
                """
                MERGE (u:User {id: $user_id})
                ON CREATE SET u.email = $user_email
                ON MATCH SET u.email = $user_email

                MERGE (p:Problem {id: $problem_id})
                SET p.title = $problem_title,
                    p.difficulty = $difficulty

                WITH u, p
                UNWIND $algorithms AS algo_name
                MERGE (c:Concept {name: algo_name})
                MERGE (p)-[:REQUIRES_CONCEPT]->(c)
                """,
                user_id=user_id,
                user_email=user_email,
                problem_id=problem_id,
                problem_title=problem_title,
                difficulty=diff,
                algorithms=problem_algorithms,
            )

            if status == "AC":
                # 2. Case AC: Create SOLVED edge, decrease WEAK_IN weights, remove FAILED edge
                session.run(
                    """
                    MATCH (u:User {id: $user_id})
                    MATCH (p:Problem {id: $problem_id})
                    
                    // Create SOLVED relationship
                    MERGE (u)-[s:SOLVED]->(p)
                    SET s.solved_at = $now
                    
                    // Delete FAILED relationship if any
                    WITH u, p
                    OPTIONAL MATCH (u)-[f:FAILED]->(p)
                    DELETE f
                    
                    // Decrease WEAK_IN weights for all concepts linked to this problem
                    WITH u, p
                    MATCH (p)-[:REQUIRES_CONCEPT]->(c:Concept)
                    MERGE (u)-[w:WEAK_IN]->(c)
                    ON CREATE SET w.weight_score = 0.0, w.last_updated = $now
                    ON MATCH SET w.weight_score = gds.math.max(0.0, w.weight_score - 1.0), w.last_updated = $now
                    """,
                    user_id=user_id,
                    problem_id=problem_id,
                    now=now_iso,
                )
                logger.info(f"Recorded AC submission in graph for user {user_id} on problem {problem_id}")

            else:
                # 3. Case non-AC (WA, TLE, RE, MLE): Create/Update FAILED edge, increase WEAK_IN weights, log ErrorType
                session.run(
                    """
                    MATCH (u:User {id: $user_id})
                    MATCH (p:Problem {id: $problem_id})
                    
                    // Merge ErrorType node and link problem to it
                    MERGE (e:ErrorType {name: $error_name})
                    MERGE (p)-[:POTENTIAL_ERROR]->(e)
                    
                    // Create or increment FAILED relationship
                    WITH u, p, e
                    MERGE (u)-[f:FAILED]->(p)
                    ON CREATE SET f.count = 1, f.last_failed_at = $now, f.last_error = $error_name
                    ON MATCH SET f.count = f.count + 1, f.last_failed_at = $now, f.last_error = $error_name
                    
                    // Increase WEAK_IN weights for all concepts linked to this problem
                    WITH u, p
                    MATCH (p)-[:REQUIRES_CONCEPT]->(c:Concept)
                    MERGE (u)-[w:WEAK_IN]->(c)
                    ON CREATE SET w.weight_score = 1.5, w.last_updated = $now
                    ON MATCH SET w.weight_score = gds.math.min(10.0, w.weight_score + 1.5), w.last_updated = $now
                    """,
                    user_id=user_id,
                    problem_id=problem_id,
                    error_name=status,
                    now=now_iso,
                )
                logger.info(f"Recorded {status} submission in graph for user {user_id} on problem {problem_id}")

        except Exception as e:
            # Check if gds.math.max is not available (standard Neo4j without GDS plugin) and fallback to pure math
            # Fallback Cypher queries using standard CASE statements instead of gds.math
            logger.warning(f"Neo4j GDS fallback triggered due to exception: {e}")
            try:
                if status == "AC":
                    session.run(
                        """
                        MATCH (u:User {id: $user_id})
                        MATCH (p:Problem {id: $problem_id})
                        MERGE (u)-[s:SOLVED]->(p)
                        SET s.solved_at = $now
                        WITH u, p
                        OPTIONAL MATCH (u)-[f:FAILED]->(p)
                        DELETE f
                        WITH u, p
                        MATCH (p)-[:REQUIRES_CONCEPT]->(c:Concept)
                        MERGE (u)-[w:WEAK_IN]->(c)
                        ON CREATE SET w.weight_score = 0.0, w.last_updated = $now
                        ON MATCH SET w.weight_score = CASE WHEN w.weight_score - 1.0 < 0.0 THEN 0.0 ELSE w.weight_score - 1.0 END, w.last_updated = $now
                        """,
                        user_id=user_id,
                        problem_id=problem_id,
                        now=now_iso,
                    )
                else:
                    session.run(
                        """
                        MATCH (u:User {id: $user_id})
                        MATCH (p:Problem {id: $problem_id})
                        MERGE (e:ErrorType {name: $error_name})
                        MERGE (p)-[:POTENTIAL_ERROR]->(e)
                        WITH u, p, e
                        MERGE (u)-[f:FAILED]->(p)
                        ON CREATE SET f.count = 1, f.last_failed_at = $now, f.last_error = $error_name
                        ON MATCH SET f.count = f.count + 1, f.last_failed_at = $now, f.last_error = $error_name
                        WITH u, p
                        MATCH (p)-[:REQUIRES_CONCEPT]->(c:Concept)
                        MERGE (u)-[w:WEAK_IN]->(c)
                        ON CREATE SET w.weight_score = 1.5, w.last_updated = $now
                        ON MATCH SET w.weight_score = CASE WHEN w.weight_score + 1.5 > 10.0 THEN 10.0 ELSE w.weight_score + 1.5 END, w.last_updated = $now
                        """,
                        user_id=user_id,
                        problem_id=problem_id,
                        error_name=status,
                        now=now_iso,
                    )
                logger.info(f"Recorded submission in graph using standard Cypher fallback for user {user_id}")
            except Exception as ex:
                logger.error(f"Failed to synchronize submission to Neo4j: {ex}")
