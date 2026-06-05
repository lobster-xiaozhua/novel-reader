'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { api } from '@/shared/lib/api';
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
  LogOut,
  Zap,
} from 'lucide-react';

const navItems = [
  { href: '/', icon: LayoutDashboard, label: '仪表盘' },
  { href: '/books', icon: BookOpen, label: '书籍管理' },
  { href: '/chapters', icon: FileText, label: '章节管理' },
  { href: '/crawler', icon: Globe, label: '爬虫任务' },
  { href: '/users', icon: Users, label: '用户管理' },
  { href: '/tags', icon: Tags, label: '标签管理' },
  { href: '/monitor', icon: Activity, label: '系统监控' },
];

export function AdminLayout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = () => {
    api.clearToken();
    router.push('/login');
  };

  return (
    <div className="flex h-screen">
      <aside
        className={`flex flex-col border-r transition-all duration-300 ${
          collapsed ? 'w-16' : 'w-60'
        }`}
        style={{
          background: 'var(--bg-secondary)',
          borderColor: 'var(--border)',
        }}
      >
        {/* Logo & Brand */}
        <div
          className="flex items-center h-16 px-4 border-b"
          style={{ borderColor: 'var(--border)' }}
        >
          <div className="flex items-center gap-3">
            <div
              className="flex items-center justify-center w-9 h-9 rounded-xl"
              style={{ background: 'var(--accent-gradient)' }}
            >
              <Zap size={18} className="text-white" />
            </div>
            {!collapsed && (
              <div className="flex flex-col">
                <span
                  className="font-bold text-base leading-tight"
                  style={{ color: 'var(--text-primary)' }}
                >
                  Admin Console
                </span>
                <span
                  className="text-xs"
                  style={{ color: 'var(--text-tertiary)' }}
                >
                  管理后台
                </span>
              </div>
            )}
          </div>
          <button
            onClick={() => setCollapsed((v) => !v)}
            className="ml-auto p-2 rounded-lg transition-all duration-200 hover:bg-white/5"
            style={{ color: 'var(--text-tertiary)' }}
          >
            {collapsed ? <Menu size={18} /> : <X size={18} />}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-5 space-y-1 px-3">
          {navItems.map(({ href, icon: Icon, label }) => {
            const isActive = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl transition-all duration-200 text-sm group"
                style={{
                  background: isActive ? 'var(--accent-soft)' : 'transparent',
                  color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                  border: isActive ? '1px solid var(--accent-strong)' : '1px solid transparent',
                }}
                title={collapsed ? label : undefined}
              >
                <Icon 
                  size={20} 
                  className="shrink-0" 
                  style={{ color: isActive ? 'var(--accent)' : 'var(--text-tertiary)' }}
                />
                {!collapsed && (
                  <span style={{ fontWeight: isActive ? 600 : 400 }}>
                    {label}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Logout */}
        <div className="p-3 border-t" style={{ borderColor: 'var(--border)' }}>
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3.5 py-2.5 rounded-xl transition-all duration-200 text-sm hover:bg-white/5"
            style={{
              color: 'var(--text-secondary)',
            }}
            title={collapsed ? '退出登录' : undefined}
          >
            <LogOut size={20} className="shrink-0" style={{ color: 'var(--text-tertiary)' }} />
            {!collapsed && <span>退出登录</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main
        className="flex-1 overflow-auto"
        style={{ background: 'var(--bg-primary)' }}
      >
        <div className="p-6 lg:p-8 max-w-7xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}