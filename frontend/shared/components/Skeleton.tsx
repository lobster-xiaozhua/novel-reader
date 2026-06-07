'use client';

export function SkeletonLine({ width = 'w-full', className = '' }: { width?: string; className?: string }) {
  return <div className={`skeleton h-4 ${width} ${className}`} />;
}

export function SkeletonCard() {
  return (
    <div className="glass-card space-y-3">
      <div className="skeleton w-full aspect-[3/4] rounded-lg" />
      <SkeletonLine width="w-3/4" />
      <SkeletonLine width="w-1/2" />
      <div className="flex gap-1">
        <div className="skeleton w-12 h-4 rounded" />
        <div className="skeleton w-16 h-4 rounded" />
      </div>
    </div>
  );
}

export function SkeletonSearch() {
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Search bar skeleton */}
      <div className="relative">
        <div className="flex items-center gap-2 glass-card p-2">
          <div className="skeleton-round w-5 h-5" />
          <div className="flex-1 skeleton h-6 rounded" />
          <div className="skeleton w-16 h-8 rounded-lg" />
        </div>
      </div>
      {/* Search results skeleton */}
      <div className="space-y-3">
        <SkeletonLine width="w-1/4" className="mb-3" />
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="glass-card p-4 flex gap-4">
            <div className="skeleton w-16 h-20 rounded flex-shrink-0" />
            <div className="flex-1 space-y-2">
              <SkeletonLine width="w-2/3" />
              <SkeletonLine width="w-1/2" />
              <SkeletonLine width="full" />
              <div className="flex gap-1">
                <div className="skeleton w-10 h-4 rounded" />
                <div className="skeleton w-14 h-4 rounded" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonBookDetail() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header skeleton */}
      <div className="glass-card overflow-hidden">
        <div className="skeleton h-32 w-full" />
        <div className="p-6 space-y-4">
          <div className="flex gap-4">
            <SkeletonLine width="w-20" />
            <SkeletonLine width="w-24" />
          </div>
          <SkeletonLine />
          <div className="flex gap-2">
            <div className="skeleton w-16 h-6 rounded-full" />
            <div className="skeleton w-20 h-6 rounded-full" />
            <div className="skeleton w-12 h-6 rounded-full" />
          </div>
          <div className="flex gap-3 pt-2">
            <div className="flex-1 skeleton h-10 rounded-lg" />
            <div className="w-24 skeleton h-10 rounded-lg" />
          </div>
        </div>
      </div>
      {/* Chapter list skeleton */}
      <div className="glass-card">
        <div className="flex items-center justify-between mb-4">
          <SkeletonLine width="w-24" />
          <SkeletonLine width="w-20" />
        </div>
        <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))' }}>
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="skeleton h-16 rounded-lg" />
          ))}
        </div>
      </div>
    </div>
  );
}

export function SkeletonHome() {
  return (
    <div className="space-y-8">
      {/* Hero section */}
      <section className="glass-card p-6 text-center space-y-2">
        <SkeletonLine width="w-1/3 mx-auto" className="h-8" />
        <SkeletonLine width="w-1/2 mx-auto" />
        <div className="pt-2">
          <div className="skeleton w-32 h-10 rounded-lg mx-auto" />
        </div>
      </section>

      {/* Categories */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <div className="skeleton-round w-5 h-5" />
          <SkeletonLine width="w-28" />
        </div>
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="skeleton w-16 h-9 rounded-lg" />
          ))}
        </div>
      </section>

      {/* Hot Today */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <div className="skeleton-round w-5 h-5" />
          <SkeletonLine width="w-32" />
        </div>
        <div className="glass-card p-2 space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 p-3">
              <div className="skeleton-round w-6 h-6 flex-shrink-0" />
              <div className="flex-1 space-y-1">
                <SkeletonLine width="w-2/3" />
                <SkeletonLine width="w-1/2" />
              </div>
              <div className="skeleton-round w-4 h-4" />
            </div>
          ))}
        </div>
      </section>

      {/* New Arrivals */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <div className="skeleton-round w-5 h-5" />
          <SkeletonLine width="w-32" />
        </div>
        <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))' }}>
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="space-y-3">
              <div className="skeleton w-full aspect-[3/4] rounded-lg" />
              <SkeletonLine />
              <SkeletonLine width="w-3/4" />
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export default {
  Line: SkeletonLine,
  Card: SkeletonCard,
  Search: SkeletonSearch,
  BookDetail: SkeletonBookDetail,
  Home: SkeletonHome,
};
