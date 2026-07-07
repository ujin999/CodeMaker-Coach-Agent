import Link from "next/link";

export default function HomePage() {
  return (
    <div className="flex flex-col items-center gap-6 py-20 text-center">
      <h1 className="text-4xl font-bold text-white">
        CodeMaker <span className="text-brand">Coach Agent</span>
      </h1>
      <p className="max-w-xl text-muted">
        정답을 대신 풀어주지 않습니다. 문제 생성 → 검증 → 풀이 → 힌트 →
        복습으로 이어지는 학습 루프로 알고리즘 실력을 키워보세요.
      </p>
      <div className="flex gap-3">
        <Link
          href="/problems"
          className="rounded-md bg-brand px-5 py-2.5 font-medium text-white hover:bg-brand-hover"
        >
          문제 둘러보기
        </Link>
        <Link
          href="/generate"
          className="rounded-md border border-border px-5 py-2.5 font-medium text-white hover:border-brand"
        >
          새 문제 생성하기
        </Link>
      </div>
    </div>
  );
}
