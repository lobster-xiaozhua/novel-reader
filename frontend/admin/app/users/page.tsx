'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import type { ApiResponse, PaginatedData, AdminUser } from '@/shared/types';

export default function UsersPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery<ApiResponse<PaginatedData<AdminUser>>>({
    queryKey: ['admin-users', page],
    queryFn: () => api.get(`/admin/users?page=${page}`),
  });

  const users = data?.data?.items ?? [];
  const total = data?.data?.total ?? 0;
  const totalPages = Math.ceil(total / 20);

  const roleMutation = useMutation({
    mutationFn: ({ id, is_staff }: { id: number; is_staff: boolean }) =>
      api.put(`/admin/users/${id}/role`, { is_staff }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
    onError: (err: Error) => alert(`操作失败: ${err.message}`),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>用户管理</h1>

      {isLoading ? (
        <div style={{ color: 'var(--text-muted)' }}>加载中...</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm" style={{ color: 'var(--text-primary)' }}>
            <thead>
              <tr className="border-b" style={{ borderColor: 'var(--border)' }}>
                <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>ID</th>
                <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>用户名</th>
                <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>邮箱</th>
                <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>角色</th>
                <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr
                  key={user.id}
                  className="border-b transition-colors hover:opacity-80"
                  style={{ borderColor: 'var(--border)' }}
                >
                  <td className="py-3 px-3" style={{ color: 'var(--text-muted)' }}>{user.id}</td>
                  <td className="py-3 px-3 font-medium">{user.username}</td>
                  <td className="py-3 px-3" style={{ color: 'var(--text-secondary)' }}>{user.email}</td>
                  <td className="py-3 px-3">
                    <span
                      className="inline-block px-2 py-0.5 rounded-full text-xs font-medium"
                      style={{
                        background: user.is_staff ? 'var(--accent-soft)' : 'rgba(59,130,246,0.12)',
                        color: user.is_staff ? 'var(--accent)' : 'var(--info)',
                        border: `1px solid ${user.is_staff ? 'var(--accent)' : 'var(--info)'}44`,
                      }}
                    >
                      {user.is_staff ? '管理员' : '读者'}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <button
                      onClick={() =>
                        roleMutation.mutate({ id: user.id, is_staff: !user.is_staff })
                      }
                      disabled={roleMutation.isPending}
                      className="text-sm font-medium disabled:opacity-40 transition-colors hover:underline"
                      style={{ color: user.is_staff ? 'var(--danger)' : 'var(--accent)' }}
                    >
                      {user.is_staff ? '降级' : '升级'}
                    </button>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-8 text-center" style={{ color: 'var(--text-muted)' }}>
                    暂无用户
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between">
            <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
              共 {total} 条，第 {page} / {totalPages} 页
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="glass-btn text-sm disabled:opacity-40"
              >
                上一页
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="glass-btn text-sm disabled:opacity-40"
              >
                下一页
              </button>
            </div>
          </div>
        )}
      )}
    </div>
  );
}