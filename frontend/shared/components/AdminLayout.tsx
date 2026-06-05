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
    <div className="admin-layout">
      <aside className="admin-sidebar">
        <div className="flex items-center justify-between mb-6 pl-1">
          {!collapsed && (
            <div>
              <h1 className="text-xl font-extrabold tracking-tight" style={{ color: 'var(--accent)' }}>
                管理后台
              </h1>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                全站控制
              </p>
            </div>
          )}
          <button
            onClick={() => setCollapsed((v) => !v)}
            className="p-1.5 rounded-lg transition-all hover:bg-white/5"
            style={{ color: 'var(--text-secondary)' }}
            title={collapsed ? '展开菜单' : '收起菜单'}
          >
            {collapsed ? <Menu size={19} strokeWidth={1.7} /> : <X size={19} strokeWidth={1.7} />}
          </button>
        </div>

        <nav className="flex-1 flex flex-col gap-1">
          {navItems.map(({ href, icon: Icon, label }) => {
            const isActive = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className="sidebar-icon"
                style={{
                  background: isActive ? 'linear-gradient(135deg, rgba(245,158,11,0.18), rgba(245,158,11,0.05))' : 'transparent',
                  borderColor: isActive ? 'rgba(245,158,11,0.2)' : 'transparent',
                  color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                  boxShadow: isActive ? '0 0 24px rgba(245,158,11,0.08), inset 0 1px 0 rgba(245,158,11,0.12)' : 'none',
                  border: isActive ? '1px solid' : '1px solid transparent',
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  padding: collapsed ? '0.75rem 0.5rem' : '0.75rem 0.9375rem',
                }}
                title={collapsed ? label : undefined}
              >
                <Icon size={collapsed ? 20 : 19} strokeWidth={collapsed ? 1.8 : 1.7} className="shrink-0" />
                {!collapsed && <span>{label}</span>}
              </Link>
            );
          })}
        </nav>
      </aside>
      <main className="admin-main">{children}</main>
    </div>
  );
}