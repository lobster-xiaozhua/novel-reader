'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import type { ApiResponse, CrawlerTask } from '@/shared/types';

const statusColors: Record<string, string> = {
  pending: '#6e7681',
  running: '#3b82f6',
  completed: '#10b981',
  failed: '#ef4444',
  stopped: '#f59e0b',
};

const statusLabels: Record<string, string> = {
  pending: '等待中',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
  stopped: '已停止',
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className="inline-block px-2 py-0.5 rounded-full text-xs font-medium"
      style={{
        background: `${statusColors[status] || '#6e7681'}22`,
        color: statusColors[status] || '#6e7681',
        border: `1px solid ${statusColors[status] || '#6e7681'}44`,
      }}
    >
      {statusLabels[status] || status}
    </span>
  );
}

export default function CrawlerPage() {
  const [url, setUrl] = useState('');
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<ApiResponse<CrawlerTask[]>>({
    queryKey: ['admin-crawler'],
    queryFn: () => api.get('/admin/crawler'),
    refetchInterval: 5000,
  });

  const tasks = data?.data ?? [];

  const createMutation = useMutation({
    mutationFn: () => api.post('/admin/crawler', { url }),
    onSuccess: () => {
      setUrl('');
      queryClient.invalidateQueries({ queryKey: ['admin-crawler'] });
    },
    onError: (err: Error) => alert(`创建失败: ${err.message}`),
  });

  const stopMutation = useMutation({
    mutationFn: (taskId: number) => api.post(`/admin/crawler/${taskId}/stop`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-crawler'] });
    },
    onError: (err: Error) => alert(`停止失败: ${err.message}`),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>爬虫控制</h1>

      <div className="flex gap-3">
        <input
          type="text"
          placeholder="输入小说源URL..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="glass-input flex-1"
        />
        <button
          onClick={() => createMutation.mutate()}
          disabled={!url || createMutation.isPending}
          className="glass-btn font-medium disabled:opacity-40"
          style={{ color: 'var(--accent)' }}
        >
          {createMutation.isPending ? '创建中...' : '创建任务'}
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
                <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>URL</th>
                <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>状态</th>
                <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>进度</th>
                <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <tr
                  key={task.id}
                  className="border-b transition-colors hover:opacity-80"
                  style={{ borderColor: 'var(--border)' }}
                >
                  <td className="py-3 px-3" style={{ color: 'var(--text-muted)' }}>{task.id}</td>
                  <td className="py-3 px-3 max-w-[300px] truncate" title={task.url}>
                    {task.url}
                  </td>
                  <td className="py-3 px-3">
                    <StatusBadge status={task.status} />
                  </td>
                  <td className="py-3 px-3" style={{ color: 'var(--accent)' }}>
                    {task.downloaded_chapters}/{task.total_chapters || '?'}
                  </td>
                  <td className="py-3 px-3">
                    {task.status === 'running' && (
                      <button
                        onClick={() => stopMutation.mutate(task.id)}
                        disabled={stopMutation.isPending}
                        className="text-sm font-medium disabled:opacity-40 transition-colors hover:underline"
                        style={{ color: 'var(--danger)' }}
                      >
                        停止
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {tasks.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-8 text-center" style={{ color: 'var(--text-muted)' }}>
                    暂无任务
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