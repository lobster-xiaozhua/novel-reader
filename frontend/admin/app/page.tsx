'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import type { ApiResponse, PerfMetrics, HealthStatus } from '@/shared/types';

function StatCard({ label, value, unit = '' }: { label: string; value: number | string; unit?: string }) {
  return (
    <div
      className="glass-card p-5 flex flex-col gap-2"
    >
      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{label}</span>
      <span className="text-3xl font-bold" style={{ color: 'var(--accent)' }}>
        {value}{unit}
      </span>
    </div>
  );
}

function HealthBadge({ label, status }: { label: string; status: string }) {
  const ok = status === 'ok' || status === 'healthy';
  return (
    <span className="inline-flex items-center gap-1.5 text-sm" style={{ color: 'var(--text-primary)' }}>
      <span
        className="inline-block w-2 h-2 rounded-full"
        style={{ background: ok ? 'var(--success)' : 'var(--danger)' }}
      />
      {label}: {status}
    </span>
  );
}

export default function DashboardPage() {
  const { data: perfData, isLoading: perfLoading } = useQuery<ApiResponse<PerfMetrics>>({
    queryKey: ['admin-perf'],
    queryFn: () => api.get('/admin/monitor/perf'),
    refetchInterval: 30000,
  });

  const { data: healthData, isLoading: healthLoading } = useQuery<ApiResponse<HealthStatus>>({
    queryKey: ['admin-health'],
    queryFn: () => api.get('/admin/monitor/health'),
    refetchInterval: 60000,
  });

  const perf = perfData?.data;
  const health = healthData?.data;

  if (perfLoading && healthLoading) {
    return (
      <div className="flex items-center justify-center h-64" style={{ color: 'var(--text-muted)' }}>
        加载中...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>仪表盘</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="总书籍数" value={perf?.books ?? '-'} />
        <StatCard label="总章节数" value={perf?.chapters ?? '-'} />
        <StatCard label="用户数" value={perf?.users ?? '-'} />
        <StatCard label="标签数" value={perf?.tags ?? '-'} />
      </div>

      {health && (
        <div className="glass-card p-5">
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>系统健康</h2>
          <div className="flex flex-wrap gap-6">
            <HealthBadge label="数据库" status={health.database ? 'ok' : 'error'} />
            <HealthBadge label="缓存" status={health.cache ? 'ok' : 'error'} />
            <HealthBadge label="系统" status={health.status} />
          </div>
        </div>
      )}
    </div>
  );
}