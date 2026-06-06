'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import type { ApiResponse, UserStats } from '@/shared/types';

function StatCard({ value, label }: { value: number | string; label: string }) {
  return (
    <div className="stat-card">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

export default function StatsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['stats'],
    queryFn: () => api.get<ApiResponse<UserStats>>('/reader/stats'),
  });

  if (isLoading) return <div className="text-center py-10" style={{ color: 'var(--text-muted)' }}>加载中...</div>;
  if (error) return <div className="text-center py-10" style={{ color: 'var(--danger)' }}>加载失败</div>;

  const stats = data?.data;

  // 7-day chart
  const chart = stats?.chart || [];
  const maxVal = Math.max(1, ...chart.map((d) => d.minutes));

  return (
    <div>
      {/* Stat cards */}
      <div className="grid gap-3 mb-6" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))' }}>
        <StatCard value={stats?.total_books ?? 0} label="总藏书" />
        <StatCard value={stats?.favorite_count ?? 0} label="收藏数" />
        <StatCard value={stats?.week_chapters ?? 0} label="本周阅读章节" />
        <StatCard value={stats?.today_minutes ?? 0} label="今日阅读(分钟)" />
      </div>

      {/* 7-day chart */}
      <div className="glass-card">
        <h3 className="text-base font-semibold mb-4">近7天阅读时长</h3>
        {chart.length > 0 ? (
          <div>
            <div className="flex items-end gap-1" style={{ height: 140, padding: '0 0 4px' }}>
              {chart.map((d, i) => (
                <div key={i} className="flex-1 flex flex-col items-center gap-1" style={{ height: '100%', justifyContent: 'flex-end' }}>
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{d.minutes}m</span>
                  <div
                    className="chart-bar"
                    style={{ height: `${(d.minutes / maxVal) * 100}%` }}
                  />
                  <span className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                    {d.date.slice(5)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>暂无数据</p>
        )}
      </div>
    </div>
  );
}