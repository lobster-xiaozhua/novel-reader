'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/shared/lib/api';
import { LogIn } from 'lucide-react';

export default function AdminLoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const res = await api.post('/auth/login', { username, password });
      const token = (res as { data: { tokens: { access_token: string } } }).data.tokens.access_token;
      api.setToken(token); // 现在会同时存 localStorage 和 cookie
      router.push('/');
    } catch (err: unknown) {
      setError((err as { message?: string })?.message || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'linear-gradient(135deg, #1f2937 0%, #111827 100%)' }}>
      <div className="glass-card max-w-md w-full p-8">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full mb-4" style={{ background: 'linear-gradient(135deg, #f59e0b, #fbbf24)', boxShadow: '0 0 30px rgba(245,158,11,0.3)' }}>
            <LogIn size={28} strokeWidth={2} style={{ color: '#1f2937' }} />
          </div>
          <h1 className="text-3xl font-extrabold" style={{ color: '#f59e0b' }}>
            管理后台
          </h1>
          <p className="mt-2" style={{ color: 'var(--text-muted)' }}>
            请登录以继续
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block mb-2 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
              用户名
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="请输入用户名"
              className="glass-input w-full"
              autoFocus
            />
          </div>
          <div>
            <label className="block mb-2 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
              密码
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
              className="glass-input w-full"
            />
          </div>
          {error && (
            <div className="p-3 rounded-lg text-sm" style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#fca5a5' }}>
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {loading ? '登录中...' : '登录'}
          </button>
        </form>

        <div className="mt-6 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
          <p>默认演示账号：</p>
          <p className="mt-1">admin / admin123</p>
        </div>
      </div>
    </div>
  );
}
