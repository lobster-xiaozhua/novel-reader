'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { api } from '@/shared/lib/api';
import type { ApiResponse, DiscoverFeed, RankingBook } from '@/shared/types';

function BookCard({ book }: { book: RankingBook }) {
  return (
    <Link href={`/book/${book.id}`} className="glass-card block no-underline">
      <div className="gradient-bar" style={{ background: `linear-gradient(90deg, ${book.gradient[0]}, ${book.gradient[1]})` }} />
      <h3 className="text-sm font-semibold truncate" style={{ color: 'var(--text)' }}>{book.title}</h3>
      <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{book.author}</p>
      <div className="flex gap-1 mt-2">
        {book.tags?.slice(0, 3).map((t) => (
          <span key={t.id} className="text-xs px-1.5 py-0.5 rounded" style={{ background: 'rgba(99,102,241,0.12)', color: 'var(--accent)' }}>
            {t.name}
          </span>
        ))}
      </div>
    </Link>
  );
}

function RankingCard({ rank, book }: { rank: number; book: RankingBook }) {
  return (
    <Link href={`/book/${book.id}`} className="glass-card flex items-center gap-3 no-underline">
      <span className="rank-num">{rank}</span>
      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-semibold truncate" style={{ color: 'var(--text)' }}>{book.title}</h4>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{book.author} · {book.chapter_count}章</p>
      </div>
    </Link>
  );
}

export default function DiscoverPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['discover'],
    queryFn: () => api.get<ApiResponse<DiscoverFeed>>('/reader/discover'),
  });

  if (isLoading) return <div className="text-center py-10" style={{ color: 'var(--text-muted)' }}>加载中...</div>;
  if (error) return <div className="text-center py-10" style={{ color: 'var(--danger)' }}>加载失败，请稍后重试</div>;

  const feed = data?.data;
  if (!feed) return null;

  const categories = [...new Set([
    ...(feed.hot_today || []).map((b) => b.category),
    ...(feed.hot_week || []).map((b) => b.category),
    ...(feed.new_arrivals || []).map((b) => b.category),
  ])];

  return (
    <div>
      {/* Categories */}
      <section className="mb-6">
        <div className="flex flex-wrap gap-2">
          {categories.map((cat) => (
            <Link
              key={cat}
              href={`/search?q=${encodeURIComponent(cat)}`}
              className="glass-card inline-block text-sm px-3 py-1.5 no-underline"
              style={{ color: 'var(--text)' }}
            >
              {cat}
            </Link>
          ))}
        </div>
      </section>

      {/* Recommendations */}
      {feed.new_arrivals?.length > 0 && (
        <section className="mb-6">
          <h2 className="text-base font-semibold mb-3">新书推荐</h2>
          <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))' }}>
            {feed.new_arrivals.slice(0, 8).map((b) => (
              <BookCard key={b.id} book={b} />
            ))}
          </div>
        </section>
      )}

      {/* Hot Today */}
      {feed.hot_today?.length > 0 && (
        <section className="mb-6">
          <h2 className="text-base font-semibold mb-3">今日热门</h2>
          <div className="flex flex-col gap-2">
            {feed.hot_today.map((b, i) => (
              <RankingCard key={b.id} rank={i + 1} book={b} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}