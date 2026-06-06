'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/shared/lib/api';
import type { AuthResponse } from '@/shared/types';

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const endpoint = mode === 'login' ? '/auth/login' : '/auth/register';
      const body = mode === 'login'
        ? { username, password }
        : { username, password, email: email || undefined };

      const res = await api.post<AuthResponse>(endpoint, body);

      if (res.access_token) {
        api.setToken(res.access_token);
      }
      if (res.refresh_token) {
        localStorage.setItem('refresh_token', res.refresh_token);
      }
      router.push('/');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '操作失败';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center" style={{ minHeight: '80vh' }}>
      <div className="glass-card w-full" style={{ maxWidth: 400 }}>
        <h1 className="text-xl font-bold text-center mb-6">
          {mode === 'login' ? '登录' : '注册'}
        </h1>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            className="glass-input"
            type="text"
            placeholder="用户名"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
          <input
            className="glass-input"
            type="password"
            placeholder="密码"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {mode === 'register' && (
            <input
              className="glass-input"
              type="email"
              placeholder="邮箱（选填）"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          )}

          {error && (
            <p className="text-sm" style={{ color: 'var(--danger)' }}>{error}</p>
          )}

          <button className="btn-primary w-full justify-center" type="submit" disabled={loading}>
            {loading ? '处理中...' : mode === 'login' ? '登录' : '注册'}
          </button>
        </form>

        <p className="text-center text-sm mt-4" style={{ color: 'var(--text-muted)' }}>
          {mode === 'login' ? '没有账号？' : '已有账号？'}
          <button
            className="ml-1 underline cursor-pointer"
            style={{ color: 'var(--accent)', background: 'none', border: 'none' }}
            onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}
          >
            {mode === 'login' ? '去注册' : '去登录'}
          </button>
        </p>
      </div>
    </div>
  );
}