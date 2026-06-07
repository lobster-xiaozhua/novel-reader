'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Home, Library, Search, BarChart3, BookOpen, Clock } from 'lucide-react';
import { api } from '@/shared/lib/api';
import type { ReadingProgress } from '@/shared/types';

const NAV = [
  { href: '/', icon: Home, label: '发现' },
  { href: '/shelf', icon: Library, label: '书架' },
  { href: '/search', icon: Search, label: '搜索' },
  { href: '/stats', icon: BarChart3, label: '统计' },
];

function RecentReadings() {
  const router = useRouter();
  const [progress, setProgress] = useState<ReadingProgress[]>([]);

  useEffect(() => {
    api.get<any>('/reader/progress?page_size=3')
      .then(res => setProgress(res.data?.items || []))
      .catch(() => {});
  }, []);

  if (progress.length === 0) {
    return (
      <div className="glass-card">
        <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
          <Clock size={14} /> 最近阅读
        </h3>
        <p className="text-xs text-[var(--text-muted)]">暂无阅读记录</p>
      </div>
    );
  }

  return (
    <div className="glass-card">
      <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
        <Clock size={14} /> 最近阅读
      </h3>
      <div className="space-y-2">
        {progress.map(p => (
          <button
            key={p.book?.id}
            className="w-full text-left p-2 rounded hover:bg-[var(--bg-secondary)] transition-colors"
            onClick={() => router.push(`/read/${p.book?.id}?chapter=${p.chapter?.id}`)}
          >
            <p className="text-sm font-medium truncate">{p.book?.title}</p>
            <p className="text-xs truncate text-[var(--text-muted)]">
              第{p.chapter?.chapter_number}章 · {p.chapter?.title}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}

export function ReaderLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="reader-layout" suppressHydrationWarning>
      {/* Left Sidebar — visible on desktop (≥992px) */}
      <nav className="reader-sidebar" suppressHydrationWarning>
        {NAV.map(({ href, icon: Icon, label }) => (
          <Link
            key={href}
            href={href}
            className={`sidebar-icon${pathname === href ? ' active' : ''}`}
          >
            <Icon size={18} />
            <span>{label}</span>
          </Link>
        ))}
      </nav>

      {/* Main Content */}
      <main className="reader-main">
        {children}
      </main>

      {/* Right Sidebar — visible on desktop (≥992px) */}
      <aside className="reader-right">
        <RecentReadings />
      </aside>

      {/* Bottom Nav — visible on mobile (<992px) */}
      <nav className="bottom-nav" suppressHydrationWarning>
        {NAV.map(({ href, icon: Icon, label }) => (
          <Link
            key={href}
            href={href}
            className={pathname === href ? 'active' : ''}
          >
            <Icon size={20} />
            <span>{label}</span>
          </Link>
        ))}
      </nav>
    </div>
  );
}