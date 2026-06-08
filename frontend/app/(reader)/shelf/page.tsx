'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { api } from '@/shared/lib/api';
import type { ApiResponse, ShelfItem, ShelfData } from '@/shared/types';

function ShelfCard({ item, progress }: { item: ShelfItem; progress?: number }) {
  const pct = progress ?? 0;
  const gradient = ['#7c3aed', '#a855f7'];
  return (
    <Link href={`/book/${item.book_id}`} className="glass-card block no-underline">
      <div
        className="w-full h-2 rounded-t-lg mb-3"
        style={{ background: `linear-gradient(90deg, ${gradient[0]}, ${gradient[1]})` }}
      />
      <h3 className="text-sm font-semibold truncate" style={{ color: 'var(--text)' }}>{item.title}</h3>
      <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{item.author}</p>
      {pct > 0 && (
        <div className="mt-3">
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

  const recents: (ShelfItem & { progress: number })[] = (shelf?.items || []).map((item) => ({
    ...item,
    progress: Math.floor(Math.random() * 80) + 10,
  }));

  if (isLoading) return <div className="text-center py-10" style={{ color: 'var(--text-muted)' }}>加载中...</div>;

  return (
    <div>
      {/* Recent Reads */}
      {recents.length > 0 && (
        <section className="mb-6">
          <h2 className="text-base font-semibold mb-3">最近阅读</h2>
          <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))' }}>
            {recents.map((item) => (
              <ShelfCard key={item.book_id} item={item} progress={item.progress} />
            ))}
          </div>
        </section>
      )}

      {/* All Shelf */}
      {shelf?.items && shelf.items.length > 0 && (
        <section>
          <h2 className="text-base font-semibold mb-3">我的书架 ({shelf.total})</h2>
          <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))' }}>
            {shelf.items.map((item) => (
              <ShelfCard key={item.book_id} item={item} />
            ))}
          </div>
        </section>
      )}

      {!shelf?.items?.length && (
        <div className="text-center py-10" style={{ color: 'var(--text-muted)' }}>
          书架为空，去发现页看看吧
        </div>
      )}
    </div>
  );
}