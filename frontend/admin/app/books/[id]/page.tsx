'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { api } from '@/shared/lib/api';
import type { ApiResponse, BookDetail } from '@/shared/types';

export default function BookEditPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<ApiResponse<BookDetail>>({
    queryKey: ['admin-book', id],
    queryFn: () => api.get(`/admin/books/${id}`),
  });

  const book = data?.data;

  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [category, setCategory] = useState('');
  const [description, setDescription] = useState('');
  const [loaded, setLoaded] = useState(false);

  if (book && !loaded) {
    setTitle(book.title);
    setAuthor(book.author);
    setCategory(book.category);
    setDescription(book.description || '');
    setLoaded(true);
  }

  const updateMutation = useMutation({
    mutationFn: () =>
      api.put(`/admin/books/${id}`, { title, author, category, description }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-books'] });
      queryClient.invalidateQueries({ queryKey: ['admin-book', id] });
      alert('保存成功');
    },
    onError: (err: Error) => alert(`保存失败: ${err.message}`),
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/admin/books/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-books'] });
      router.back();
    },
    onError: (err: Error) => alert(`删除失败: ${err.message}`),
  });

  const handleDelete = () => {
    if (window.confirm('确定要删除这本书吗？此操作不可撤销。')) {
      deleteMutation.mutate();
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64" style={{ color: 'var(--text-muted)' }}>
        加载中...
      </div>
    );
  }

  if (!book) {
    return (
      <div className="flex items-center justify-center h-64" style={{ color: 'var(--danger)' }}>
        未找到该书籍
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center gap-4">
        <button
          onClick={() => router.back()}
          className="glass-btn text-sm"
        >
          ← 返回
        </button>
        <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
          编辑书籍 #{id}
        </h1>
      </div>

      <div className="glass-card p-6 space-y-5">
        <div>
          <label
            className="block text-sm mb-1.5"
            style={{ color: 'var(--text-secondary)' }}
          >
            书名
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
            作者
          </label>
          <input
            type="text"
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
            className="glass-input w-full"
          />
        </div>

        <div>
          <label
            className="block text-sm mb-1.5"
            style={{ color: 'var(--text-secondary)' }}
          >
            分类
          </label>
          <input
            type="text"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="glass-input w-full"
          />
        </div>

        <div>
          <label
            className="block text-sm mb-1.5"
            style={{ color: 'var(--text-secondary)' }}
          >
            简介
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={5}
            className="glass-input w-full resize-y"
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
          <button
            onClick={handleDelete}
            disabled={deleteMutation.isPending}
            className="glass-btn font-medium disabled:opacity-40"
            style={{ color: 'var(--danger)' }}
          >
            {deleteMutation.isPending ? '删除中...' : '删除'}
          </button>
        </div>
      </div>
    </div>
  );
}