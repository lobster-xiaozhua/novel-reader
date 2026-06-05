'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { Home, Library, Search, BarChart3 } from 'lucide-react';

const NAV = [
  { href: '/', icon: Home, label: '发现' },
  { href: '/shelf', icon: Library, label: '书架' },
  { href: '/search', icon: Search, label: '搜索' },
  { href: '/stats', icon: BarChart3, label: '统计' },
];

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 992);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);
  return isMobile;
}

export function ReaderLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isMobile = useIsMobile();

  const Sidebar = () => (
    <nav className="reader-sidebar">
      <div className="mb-6 pl-2">
        <h1 className="text-xl font-extrabold tracking-tight" style={{ color: 'var(--text-primary)' }}>
          小说阅读器
        </h1>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
          沉浸式阅读体验
        </p>
      </div>
      {NAV.map(({ href, icon: Icon, label }) => (
        <Link
          key={href}
          href={href}
          className={`sidebar-icon${pathname === href ? ' active' : ''}`}
        >
          <Icon size={19} strokeWidth={1.7} />
          <span>{label}</span>
        </Link>
      ))}
    </nav>
  );

  const BottomNav = () => (
    <nav className="bottom-nav">
      {NAV.map(({ href, icon: Icon, label }) => (
        <Link
          key={href}
          href={href}
          className={pathname === href ? 'active' : ''}
        >
          <Icon size={20} strokeWidth={1.8} />
          <span>{label}</span>
        </Link>
      ))}
    </nav>
  );

  return (
    <div className="reader-layout">
      <Sidebar />
      <main className="reader-main" style={isMobile ? { paddingBottom: '5rem' } : undefined}>
        {children}
      </main>
      {!isMobile && (
        <aside className="reader-right">
          <div className="glass-card mb-4">
            <h3 className="text-sm font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
              继续阅读
            </h3>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              暂无阅读记录
            </p>
          </div>
          <div className="glass-card">
            <h3 className="text-sm font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
              今日目标
            </h3>
            <div className="progress-bar mb-2">
              <div className="progress-fill" style={{ width: '42%' }}></div>
            </div>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              已读 42 分钟
            </p>
          </div>
        </aside>
      )}
      {isMobile && <BottomNav />}
    </div>
  );
}