"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCurrentUser } from "@/lib/hooks";
import { clearToken } from "@/lib/auth";

const LINKS = [
  { href: "/problems", label: "문제 둘러보기" },
  { href: "/generate", label: "문제 생성" },
  { href: "/problems/mine", label: "내 문제" },
  { href: "/problems/manage", label: "문제 관리" },
];

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading } = useCurrentUser();

  function handleLogout() {
    clearToken();
    router.push("/login");
    router.refresh();
  }

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-bg/90 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <div className="flex items-center gap-8">
          <Link href="/" className="text-lg font-bold text-white">
            CodeMaker <span className="text-brand">Coach</span>
          </Link>
          <div className="hidden gap-1 sm:flex">
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                  pathname === link.href
                    ? "bg-surface-2 text-white"
                    : "text-muted hover:text-white"
                }`}
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-3 text-sm">
          {loading ? null : user ? (
            <>
              <span className="text-muted">
                {user.display_name ?? user.email}
              </span>
              <button
                onClick={handleLogout}
                className="rounded-md border border-border px-3 py-1.5 text-muted hover:text-white"
              >
                로그아웃
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="rounded-md px-3 py-1.5 text-muted hover:text-white"
              >
                로그인
              </Link>
              <Link
                href="/register"
                className="rounded-md bg-brand px-3 py-1.5 font-medium text-white hover:bg-brand-hover"
              >
                회원가입
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
