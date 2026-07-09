import logging
from sqlalchemy.orm import Session
from app.models.problem import Problem
from app.models.submission import Submission
from agent.schemas import GeneratedProblem
from agent.sweeper.agent import evaluate_stub_problem, diagnose_buggy_problem

logger = logging.getLogger(__name__)


async def run_sweeper_cycle(db: Session) -> None:
    """백그라운드에서 오작동하는 불량 문제 및 더미 스텁 문제를 찾아 자동 격리/제거하는 에이전트 주기 사이클."""
    logger.info("=== Start Problem Sweeper Agent Cycle ===")

    # 1. 스텁/테스트 문제 검출 (Hard Delete 대상 후보)
    # 제목, 지문, 혹은 ID 상에 'stub' 또는 'test' 관련 키워드가 있는 활성 상태인 문제 수집
    candidates = (
        db.query(Problem)
        .filter(
            Problem.status == "active",
            (
                Problem.id.ilike("%stub%")
                | Problem.id.ilike("%test%")
                | Problem.title.ilike("%stub%")
                | Problem.title.ilike("%test%")
                | Problem.statement.ilike("%stub%")
                | Problem.statement.ilike("%test%")
            ),
        )
        .all()
    )

    deleted_count = 0
    for p in candidates:
        from agent.schemas import HintBlueprint
        # Pydantic 모델로 변환하여 에이전트 노드에 전송
        gen_prob = GeneratedProblem(
            problem_id=p.id,
            title=p.title,
            difficulty=p.difficulty,
            algorithm=p.algorithm,
            learning_goal=p.learning_goal,
            statement=p.statement,
            input_format=p.input_format,
            output_format=p.output_format,
            constraints=p.constraints,
            sample_input=p.sample_input,
            sample_output=p.sample_output,
            expected_time_complexity=p.expected_time_complexity,
            hint_blueprint=HintBlueprint(
                intended_algorithm=p.algorithm,
                core_insight=p.learning_goal or "알고리즘 구현 접근 방식",
                common_misconceptions=[],
                edge_case_focus=[],
                forbidden_disclosures=[],
                level_1_guidance="",
                level_2_guidance="",
                level_3_guidance="",
            ),
        )

        try:
            # LLM 에이전트 자율 판정 수행
            report = evaluate_stub_problem(gen_prob)
            if report.is_stub:
                logger.info(
                    f"🤖 Sweeper Agent Decision: HARD DELETE Problem '{p.title}' (ID: {p.id}). Reason: {report.reason}"
                )
                db.delete(p)
                deleted_count += 1
            else:
                logger.info(
                    f"🤖 Sweeper Agent: Problem '{p.title}' (ID: {p.id}) has stub keywords but is evaluated as a normal problem. Skipped."
                )
        except Exception as e:
            logger.error(f"Error evaluating stub check for problem {p.id}: {e}")

    if deleted_count > 0:
        db.commit()
        logger.info(f"Successfully hard-deleted {deleted_count} stub problems.")

    # 2. 고에러율 문제 분석 (Soft Delete 대상 후보)
    # 현재 활성 상태인 모든 문제들의 에러율 검토
    active_problems = db.query(Problem).filter(Problem.status == "active").all()
    soft_deleted_count = 0

    for p in active_problems:
        # 최근 10건의 제출 조회
        recent_subs = (
            db.query(Submission)
            .filter(Submission.problem_id == p.id)
            .order_by(Submission.created_at.desc())
            .limit(10)
            .all()
        )

        # 제출 건수가 최소 5건 이상 있을 때만 분석 가동
        if len(recent_subs) < 5:
            continue

        # 에러 건수(WA, TLE, RE, MLE, JUDGE_ERROR) 합산
        error_count = sum(
            1
            for s in recent_subs
            if s.status in ["WA", "TLE", "RE", "MLE", "JUDGE_ERROR"]
        )
        error_rate = error_count / len(recent_subs)

        # 에러율이 70% 이상일 때 '출제 오류 의심'군으로 락
        if error_rate >= 0.7:
            logger.info(
                f"Problem '{p.title}' (ID: {p.id}) has high error rate ({error_rate*100:.1f}%). Triggering debugger agent..."
            )

            # 유저 제출들에서 에러 덤프 생성
            error_dumps = []
            for sub in recent_subs:
                if sub.status != "AC":
                    dump_info = (
                        f"SubID: {sub.id} | Status: {sub.status}\n"
                        f"Failed Testcase: {sub.failed_testcase_name or 'N/A'}\n"
                        f"Actual Output: {sub.actual_output or 'N/A'}\n"
                        f"Expected Output: {sub.expected_output or 'N/A'}\n"
                        f"Stderr: {sub.stderr or 'None'}\n"
                        f"----------------------------------------"
                    )
                    error_dumps.append(dump_info)

            error_logs_text = "\n".join(error_dumps)
            from agent.schemas import HintBlueprint
            gen_prob = GeneratedProblem(
                problem_id=p.id,
                title=p.title,
                difficulty=p.difficulty,
                algorithm=p.algorithm,
                learning_goal=p.learning_goal,
                statement=p.statement,
                input_format=p.input_format,
                output_format=p.output_format,
                constraints=p.constraints,
                sample_input=p.sample_input,
                sample_output=p.sample_output,
                expected_time_complexity=p.expected_time_complexity,
                hint_blueprint=HintBlueprint(
                    intended_algorithm=p.algorithm,
                    core_insight=p.learning_goal or "알고리즘 구현 접근 방식",
                    common_misconceptions=[],
                    edge_case_focus=[],
                    forbidden_disclosures=[],
                    level_1_guidance="",
                    level_2_guidance="",
                    level_3_guidance="",
                ),
            )

            try:
                # LLM 디버거 에이전트 자율 진단 수행
                bug_report = diagnose_buggy_problem(
                    gen_prob, p.reference_solution, error_logs_text
                )
                if bug_report.is_faulty_problem:
                    logger.info(
                        f"🤖 Sweeper Agent Decision: SOFT DELETE (Quarantine) Problem '{p.title}' (ID: {p.id}). "
                        f"Reason: {bug_report.bug_description}"
                    )
                    p.status = "removed"  # 소프트 딜리트 상태 변경
                    db.add(p)
                    soft_deleted_count += 1
                else:
                    logger.info(
                        f"🤖 Sweeper Agent: Problem '{p.title}' (ID: {p.id}) has high error rate but is evaluated as a normal hard problem. Skipped."
                    )
            except Exception as e:
                logger.error(
                    f"Error diagnosing buggy problem checks for problem {p.id}: {e}"
                )

    if soft_deleted_count > 0:
        db.commit()
        logger.info(f"Successfully soft-deleted {soft_deleted_count} faulty problems.")

    logger.info("=== Finished Problem Sweeper Agent Cycle ===")
