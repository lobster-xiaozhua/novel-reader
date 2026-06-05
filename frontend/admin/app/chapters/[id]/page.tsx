'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { api } from '@/shared/lib/api';
import type { ApiResponse, AdminChapter } from '@/shared/types';

export default function ChapterEditPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<ApiResponse<AdminChapter>>({
    queryKey: ['admin-chapter', id],
    queryFn: () => api.get(`/admin/chapters/${id}`),
  });

  const chapter = data?.data;

  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [loaded, setLoaded] = useState(false);

  if (chapter && !loaded) {
    setTitle(chapter.title);
    setContent(chapter.content || '');
    setLoaded(true);
  }

  const updateMutation = useMutation({
    mutationFn: () =>
      api.put(`/admin/chapters/${id}`, { title, content }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-chapter'] });
      alert('保存成功');
    },
    onError: (err: Error) => alert(`保存失败: ${err.message}`),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64" style={{ color: 'var(--text-muted)' }}>
        加载中...
      </div>
    );
  }

  if (!chapter) {
    return (
      <div className="flex items-center justify-center h-64" style={{ color: 'var(--danger)' }}>
        未找到该章节
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button
          onClick={() => router.back()}
          className="glass-btn text-sm"
        >
          ← 返回
        </button>
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            编辑章节
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            {chapter.book_title} · 第 {chapter.chapter_number} 章
          </p>
        </div>
      </div>

      <div className="glass-card p-6 space-y-5">
        <div>
          <label
            className="block text-sm mb-1.5"
            style={{ color: 'var(--text-secondary)' }}
          >
            章节标题
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="glass-input w-full"
          />
        </div>

        <div>
          <label
            className="block text-sm mb-1.5"
            style={{ color: 'var(--text-secondary)' }}
          >
            章节内容
          </label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={20}
            className="glass-input w-full resize-y font-mono"
          />
        </div>

        <div className="flex gap-3 pt-2">
          <button
            onClick={() => updateMutation.mutate()}
            disabled={updateMutation.isPending}
            className="glass-btn font-medium disabled:opacity-40"
            style={{ color: 'var(--accent)' }}
          >
            {updateMutation.isPending ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}
