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
        <StatCard label="总书籍数" value={perf?.requests ?? '-'} />
        <StatCard label="总章节数" value={perf?.cpu ? `${perf.cpu}` : '-'} />
        <StatCard label="用户数" value={perf?.memory ? `${perf.memory}` : '-'} />
        <StatCard label="活跃任务" value={perf?.uptime ? `${Math.round(perf.uptime / 3600)}h` : '-'} />
      </div>

      {health && (
        <div className="glass-card p-5">
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>系统健康</h2>
          <div className="flex flex-wrap gap-6">
            <HealthBadge label="数据库" status={health.database} />
            <HealthBadge label="缓存" status={health.cache} />
            <HealthBadge label="系统" status={health.status} />
          </div>
        </div>
      )}

      {perf && (
        <div className="glass-card p-5">
          <h2 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>性能指标</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            <div>
              <span style={{ color: 'var(--text-muted)' }}>CPU</span>
              <p style={{ color: 'var(--text-primary)' }}>{perf.cpu}%</p>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>内存</span>
              <p style={{ color: 'var(--text-primary)' }}>{perf.memory} MB</p>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>运行时间</span>
              <p style={{ color: 'var(--text-primary)' }}>{Math.round(perf.uptime / 3600)}h</p>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>平均响应</span>
              <p style={{ color: 'var(--text-primary)' }}>{perf.avg_response_time}ms</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}