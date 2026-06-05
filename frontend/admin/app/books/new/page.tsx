'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { api } from '@/shared/lib/api';
import { useToast } from '@/shared/components/Toast';
import { ArrowLeft, BookOpen, Plus } from 'lucide-react';

export default function BookCreatePage() {
  const router = useRouter();
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [category, setCategory] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const { showToast } = useToast();

  const handleCreate = async () => {
    if (!title.trim()) {
      showToast('请输入书名', 'warning');
      return;
    }
    setLoading(true);
    try {
      const res = await api.post('/admin/books', {
        title,
        author,
        category,
        description,
      });
      const bookId = (res as any).data?.id;
      showToast('创建成功', 'success');
      if (bookId) {
        router.push(`/books/${bookId}`);
      } else {
        router.push('/books');
      }
    } catch (err: any) {
      showToast(`创建失败: ${err.message || '未知错误'}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-2xl">
      {/* Page Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => router.back()}
          className="glass-btn text-sm"
        >
          <ArrowLeft size={16} />
          返回
        </button>
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            创建书籍
          </h1>
          <p style={{ color: 'var(--text-tertiary)', marginTop: '0.25rem' }}>
            填写书籍基本信息
          </p>
        </div>
      </div>

      {/* Form Card */}
      <div className="glass-card p-7 space-y-6">
        <div>
          <label
            className="block text-sm font-medium mb-2"
            style={{ color: 'var(--text-secondary)' }}
          >
            书名 *
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="请输入书名"
            className="glass-input w-full"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <div>
            <label
              className="block text-sm font-medium mb-2"
              style={{ color: 'var(--text-secondary)' }}
            >
              作者
            </label>
            <input
              type="text"
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              placeholder="请输入作者"
              className="glass-input w-full"
            />
          </div>

          <div>
            <label
              className="block text-sm font-medium mb-2"
              style={{ color: 'var(--text-secondary)' }}
            >
              分类
            </label>
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="请输入分类"
              className="glass-input w-full"
            />
          </div>
        </div>

        <div>
          <label
            className="block text-sm font-medium mb-2"
            style={{ color: 'var(--text-secondary)' }}
          >
            简介
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={6}
            placeholder="请输入书籍简介"
            className="glass-input w-full resize-y"
          />
        </div>

        <div className="flex gap-3 pt-4 border-t" style={{ borderColor: 'var(--border)' }}>
          <button
            onClick={handleCreate}
            disabled={loading}
            className="glass-btn glass-btn-primary font-medium disabled:opacity-40"
          >
            <Plus size={16} />
            {loading ? '创建中...' : '创建书籍'}
          </button>
          <button
            onClick={() => router.back()}
            disabled={loading}
            className="glass-btn font-medium disabled:opacity-40"
          >
            取消
          </button>
        </div>
      </div>
    </div>
  );
}
