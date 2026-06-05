'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import type { ApiResponse, PerfMetrics, HealthStatus } from '@/shared/types';

function StatCard({ label, value, unit = '' }: { label: string; value: number | string; unit?: string }) {
  return (
    <div className="glass-card p-5 flex flex-col gap-2">
      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{label}</span>
      <span className="text-3xl font-bold" style={{ color: 'var(--accent)' }}>
        {value}{unit}
      </span>
    </div>
  );
}

export default function MonitorPage() {
  const { data: perfData, isLoading: perfLoading } = useQuery<ApiResponse<PerfMetrics>>({
    queryKey: ['admin-perf'],
    queryFn: () => api.get('/admin/monitor/perf'),
    refetchInterval: 15000,
  });

  const { data: healthData, isLoading: healthLoading } = useQuery<ApiResponse<HealthStatus>>({
    queryKey: ['admin-health'],
    queryFn: () => api.get('/admin/monitor/health'),
    refetchInterval: 30000,
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
      <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>系统监控</h1>

      {perf && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="总书籍" value={perf.books} />
          <StatCard label="总章节" value={perf.chapters} />
          <StatCard label="用户数" value={perf.users} />
          <StatCard label="标签数" value={perf.tags} />
        </div>
      )}

      {health && (
        <div className="glass-card p-5">
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
            健康状态
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <span className="text-sm" style={{ color: 'var(--text-muted)' }}>系统状态</span>
              <p
                className="text-lg font-semibold mt-1"
                style={{ color: health.status === 'healthy' ? 'var(--success)' : 'var(--danger)' }}
              >
                {health.status}
              </p>
            </div>
            <div>
              <span className="text-sm" style={{ color: 'var(--text-muted)' }}>数据库</span>
              <p
                className="text-lg font-semibold mt-1"
                style={{ color: health.database ? 'var(--success)' : 'var(--danger)' }}
              >
                {health.database ? '正常' : '异常'}
              </p>
            </div>
            <div>
              <span className="text-sm" style={{ color: 'var(--text-muted)' }}>缓存</span>
              <p
                className="text-lg font-semibold mt-1"
                style={{ color: health.cache ? 'var(--success)' : 'var(--danger)' }}
              >
                {health.cache ? '正常' : '异常'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}