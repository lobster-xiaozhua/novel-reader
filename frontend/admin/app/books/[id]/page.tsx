'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import Link from 'next/link';
import { api } from '@/shared/lib/api';
import { useToast } from '@/shared/components/Toast';
import type { ApiResponse, BookDetail } from '@/shared/types';

export default function BookEditPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const { data, isLoading } = useQuery<ApiResponse<BookDetail>>({
    queryKey: ['admin-book', id],
    queryFn: () => api.get(`/admin/books/${id}`),
  });

  const book = data?.data;

  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [category, setCategory] = useState('');
  const [description, setDescription] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    if (book) {
      setTitle(book.title);
      setAuthor(book.author);
      setCategory(book.category);
      setDescription(book.description || '');
    }
  }, [book]);

  const updateMutation = useMutation({
    mutationFn: () =>
      api.put(`/admin/books/${id}`, { title, author, category, description }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-books'] });
      queryClient.invalidateQueries({ queryKey: ['admin-book', id] });
      showToast('保存成功', 'success');
    },
    onError: (err: Error) => showToast(`保存失败: ${err.message}`, 'error'),
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/admin/books/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-books'] });
      router.back();
    },
    onError: (err: Error) => showToast(`删除失败: ${err.message}`, 'error'),
  });

  const handleDelete = () => {
    deleteMutation.mutate();
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
    <div className="space-y-6">
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

      <div className="glass-card p-4">
        <div className="flex items-center gap-3">
          <Link
            href={`/chapters?book_id=${id}`}
            className="glass-btn font-medium"
            style={{ color: 'var(--accent)' }}
          >
            📚 管理章节 ({book?.chapter_count || book?.total_chapters || 0})
          </Link>
          <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
            点击进入章节列表，可以编辑或删除章节
          </span>
        </div>
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
          {!confirmDelete ? (
            <button
              onClick={() => setConfirmDelete(true)}
              disabled={deleteMutation.isPending}
              className="glass-btn font-medium disabled:opacity-40"
              style={{ color: 'var(--danger)' }}
            >
              删除
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <span style={{ color: 'var(--text-muted)' }}>确定删除？</span>
              <button
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
                className="glass-btn font-medium disabled:opacity-40"
                style={{ color: 'var(--danger)' }}
              >
                {deleteMutation.isPending ? '删除中...' : '确认'}
              </button>
              <button
                onClick={() => setConfirmDelete(false)}
                disabled={deleteMutation.isPending}
                className="glass-btn font-medium disabled:opacity-40"
              >
                取消
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}