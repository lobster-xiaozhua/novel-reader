'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  BookOpen,
  FileText,
  Globe,
  Users,
  Tags,
  Activity,
  Menu,
  X,
} from 'lucide-react';

const navItems = [
  { href: '/', icon: LayoutDashboard, label: '仪表盘' },
  { href: '/books', icon: BookOpen, label: '书籍' },
  { href: '/chapters', icon: FileText, label: '章节' },
  { href: '/crawler', icon: Globe, label: '爬虫' },
  { href: '/users', icon: Users, label: '用户' },
  { href: '/tags', icon: Tags, label: '标签' },
  { href: '/monitor', icon: Activity, label: '监控' },
];

export function AdminLayout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  return (
    <div className="flex h-screen">
      <aside
        className={`flex flex-col border-r transition-all duration-300 ${
          collapsed ? 'w-16' : 'w-56'
        }`}
        style={{
          background: 'var(--bg-secondary)',
          borderColor: 'var(--border)',
        }}
      >
        <div
          className="flex items-center h-14 px-4 border-b"
          style={{ borderColor: 'var(--border)' }}
        >
          {!collapsed && (
            <span
              className="font-bold text-lg truncate"
              style={{ color: 'var(--accent)' }}
            >
              Admin
            </span>
          )}
          <button
            onClick={() => setCollapsed((v) => !v)}
            className="ml-auto p-1.5 rounded-lg transition-colors hover:opacity-80"
            style={{ color: 'var(--text-secondary)' }}
          >
            {collapsed ? <Menu size={18} /> : <X size={18} />}
          </button>
        </div>
        <nav className="flex-1 py-4 space-y-1 px-2">
          {navItems.map(({ href, icon: Icon, label }) => {
            const isActive = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-sm ${
                  isActive ? 'font-semibold' : ''
                }`}
                style={{
                  background: isActive ? 'var(--accent-soft)' : 'transparent',
                  color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                }}
                title={collapsed ? label : undefined}
              >
                <Icon size={20} className="shrink-0" />
                {!collapsed && <span>{label}</span>}
              </Link>
            );
          })}
        </nav>
      </aside>
      <main
        className="flex-1 overflow-auto p-6"
        style={{ background: 'var(--bg-primary)' }}
      >
        {children}
      </main>
    </div>
  );
}