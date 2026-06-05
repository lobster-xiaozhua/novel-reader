'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import type { ApiResponse, TagWithCount } from '@/shared/types';

export default function TagsPage() {
  const [name, setName] = useState('');
  const [color, setColor] = useState('#f59e0b');
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<ApiResponse<TagWithCount[]>>({
    queryKey: ['admin-tags'],
    queryFn: () => api.get('/admin/tags'),
  });

  const tags = data?.data ?? [];

  const createMutation = useMutation({
    mutationFn: () => api.post('/admin/tags', { name, color }),
    onSuccess: () => {
      setName('');
      setColor('#f59e0b');
      queryClient.invalidateQueries({ queryKey: ['admin-tags'] });
    },
    onError: (err: Error) => alert(`创建失败: ${err.message}`),
  });

  const deleteMutation = useMutation({
    mutationFn: (tagId: number) => api.delete(`/admin/tags/${tagId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-tags'] });
    },
    onError: (err: Error) => alert(`删除失败: ${err.message}`),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>标签管理</h1>

      <div className="glass-card p-5 flex items-end gap-3 flex-wrap">
        <div>
          <label className="block text-sm mb-1.5" style={{ color: 'var(--text-secondary)' }}>
            名称
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="标签名"
            className="glass-input"
          />
        </div>
        <div>
          <label className="block text-sm mb-1.5" style={{ color: 'var(--text-secondary)' }}>
            颜色
          </label>
          <input
            type="color"
            value={color}
            onChange={(e) => setColor(e.target.value)}
            className="w-10 h-9 rounded cursor-pointer border-0"
          />
        </div>
        <button
          onClick={() => createMutation.mutate()}
          disabled={!name || createMutation.isPending}
          className="glass-btn font-medium disabled:opacity-40"
          style={{ color: 'var(--accent)' }}
        >
          {createMutation.isPending ? '创建中...' : '创建'}
        </button>
      </div>

      {isLoading ? (
        <div style={{ color: 'var(--text-muted)' }}>加载中...</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm" style={{ color: 'var(--text-primary)' }}>
            <thead>
              <tr className="border-b" style={{ borderColor: 'var(--border)' }}>
                <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>ID</th>
                <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>名称</th>
                <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>颜色</th>
                <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>书籍数</th>
                <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {tags.map((tag) => (
                <tr
                  key={tag.id}
                  className="border-b transition-colors hover:opacity-80"
                  style={{ borderColor: 'var(--border)' }}
                >
                  <td className="py-3 px-3" style={{ color: 'var(--text-muted)' }}>{tag.id}</td>
                  <td className="py-3 px-3">
                    <span
                      className="inline-block px-2 py-0.5 rounded-full text-xs font-medium"
                      style={{
                        background: `${tag.color || '#f59e0b'}22`,
                        color: tag.color || '#f59e0b',
                        border: `1px solid ${tag.color || '#f59e0b'}44`,
                      }}
                    >
                      {tag.name}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <div className="flex items-center gap-2">
                      <span
                        className="inline-block w-4 h-4 rounded"
                        style={{ background: tag.color || '#f59e0b' }}
                      />
                      <span style={{ color: 'var(--text-muted)' }}>{tag.color || '-'}</span>
                    </div>
                  </td>
                  <td className="py-3 px-3" style={{ color: 'var(--accent)' }}>{tag.book_count}</td>
                  <td className="py-3 px-3">
                    <button
                      onClick={() => {
                        if (window.confirm('确定删除此标签？')) {
                          deleteMutation.mutate(tag.id);
                        }
                      }}
                      disabled={deleteMutation.isPending}
                      className="text-sm font-medium disabled:opacity-40 transition-colors hover:underline"
                      style={{ color: 'var(--danger)' }}
                    >
                      删除
                    </button>
                  </td>
                </tr>
              ))}
              {tags.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-8 text-center" style={{ color: 'var(--text-muted)' }}>
                    暂无标签
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}