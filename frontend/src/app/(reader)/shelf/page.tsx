'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { api } from '@/lib/api';
import type { ApiResponse, ShelfData } from '@/types';

interface ShelfBook {
  id: number;
  book_id: number;
  title: string;
  author: string;
  category: string;
  gradient?: [string, string];
  chapter_count: number;
  progress: { chapter_id: number; position: number } | null;
  created_at: string;
}

function ShelfCard({ item }: { item: ShelfBook }) {
  // 计算阅读进度百分比（基于章节位置）
  const pct = item.progress && item.chapter_count > 0
    ? Math.round((item.progress.chapter_id / item.chapter_count) * 100)
    : 0;
  return (
    <Link href={`/book/${item.book_id}`} className="glass-card block no-underline">
      <div
        className="gradient-bar"
        style={{ background: item.gradient ? `linear-gradient(90deg, ${item.gradient[0]}, ${item.gradient[1]})` : 'linear-gradient(90deg, var(--accent), var(--accent2))' }}
      />
      <h3 className="text-sm font-semibold truncate" style={{ color: 'var(--text)' }}>{item.title}</h3>
      <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{item.author}</p>
      {pct > 0 && (
        <div className="mt-2">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${pct}%` }} />
          </div>
          <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{pct}%</p>
        </div>
      )}
    </Link>
  );
}

export default function ShelfPage() {
  const { data: shelfData, isLoading } = useQuery({
    queryKey: ['shelf'],
    queryFn: () => api.get<ApiResponse<ShelfData>>('/reader/shelf'),
  });

  const shelf = shelfData?.data;

  if (isLoading) return <div className="text-center py-10" style={{ color: 'var(--text-muted)' }}>加载中...</div>;

  const favorites: ShelfBook[] = (shelf as any)?.favorites || [];
  const recentReads: ShelfBook[] = (shelf as any)?.recent_reads || [];

  return (
    <div>
      {/* 最近阅读 */}
      {recentReads.length > 0 && (
        <section className="mb-6">
          <h2 className="text-base font-semibold mb-3">最近阅读</h2>
          <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))' }}>
            {recentReads.map((item) => (
              <ShelfCard key={item.book_id} item={item} />
            ))}
          </div>
        </section>
      )}

      {/* 我的书架 */}
      {favorites.length > 0 && (
        <section>
          <h2 className="text-base font-semibold mb-3">我的书架 ({favorites.length})</h2>
          <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))' }}>
            {favorites.map((item) => (
              <ShelfCard key={item.book_id} item={item} />
            ))}
          </div>
        </section>
      )}

      {favorites.length === 0 && recentReads.length === 0 && (
        <div className="text-center py-10" style={{ color: 'var(--text-muted)' }}>
          书架为空，去发现页看看吧
        </div>
      )}
    </div>
  );
}
