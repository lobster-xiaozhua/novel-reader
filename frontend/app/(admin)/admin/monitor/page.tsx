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
          <StatCard label="CPU 使用率" value={perf.cpu} unit="%" />
          <StatCard label="内存使用" value={perf.memory} unit=" MB" />
          <StatCard label="运行时间" value={Math.round(perf.uptime / 3600)} unit="h" />
          <StatCard label="平均响应" value={perf.avg_response_time} unit="ms" />
        </div>
      )}

      {health && (
        <div className="glass-card p-5">
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
            健康状态
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
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
                style={{ color: health.database === 'ok' ? 'var(--success)' : 'var(--danger)' }}
              >
                {health.database}
              </p>
            </div>
            <div>
              <span className="text-sm" style={{ color: 'var(--text-muted)' }}>缓存</span>
              <p
                className="text-lg font-semibold mt-1"
                style={{ color: health.cache === 'ok' ? 'var(--success)' : 'var(--danger)' }}
              >
                {health.cache}
              </p>
            </div>
            <div>
              <span className="text-sm" style={{ color: 'var(--text-muted)' }}>版本</span>
              <p className="text-lg font-semibold mt-1" style={{ color: 'var(--text-primary)' }}>
                {health.version}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}