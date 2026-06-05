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
  );

  const BottomNav = () => (
    <nav className="bottom-nav">
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
  );

  return (
    <div className="reader-layout">
      <Sidebar />
      <main className="reader-main" style={isMobile ? { paddingBottom: '5rem' } : undefined}>
        {children}
      </main>
      {!isMobile && (
        <aside className="reader-right">
          <div className="glass-card">
            <h3 className="text-sm font-semibold mb-2">继续阅读</h3>
            <p className="text-xs text-gray-500">暂无阅读记录</p>
          </div>
        </aside>
      )}
      {isMobile && <BottomNav />}
    </div>
  );
}