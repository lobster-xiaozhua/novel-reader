'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import type { ApiResponse, PerfMetrics, HealthStatus } from '@/shared/types';
import { 
  BookOpen, 
  FileText, 
  Users, 
  Tags, 
  Database, 
  HardDrive, 
  Activity, 
  CheckCircle2, 
  XCircle 
} from 'lucide-react';

function StatCard({ 
  label, 
  value, 
  icon: Icon,
  color = 'var(--accent)',
  unit = '' 
}: { 
  label: string; 
  value: number | string; 
  icon: any;
  color?: string;
  unit?: string;
}) {
  return (
    <div className="glass-card p-5 flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div
          className="flex items-center justify-center w-10 h-10 rounded-xl"
          style={{ background: `${color}20` }}
        >
          <Icon size={20} style={{ color }} />
        </div>
      </div>
      <div>
        <span
          className="block text-sm"
          style={{ color: 'var(--text-tertiary)', marginBottom: '0.25rem' }}
        >
          {label}
        </span>
        <span className="block text-3xl font-bold" style={{ color }}>
          {value}
          {unit}
        </span>
      </div>
    </div>
  );
}

function HealthItem({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 rounded-xl" style={{ background: ok ? 'var(--success-soft)' : 'var(--danger-soft)' }}>
      {ok ? (
        <CheckCircle2 size={20} style={{ color: 'var(--success)' }} />
      ) : (
        <XCircle size={20} style={{ color: 'var(--danger)' }} />
      )}
      <div>
        <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
          {label}
        </p>
        <p className="text-xs" style={{ color: ok ? 'var(--success)' : 'var(--danger)' }}>
          {ok ? '运行正常' : '异常'}
        </p>
      </div>
    </div>
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
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-transparent border-t-[var(--accent)] rounded-full animate-spin" />
          <p style={{ color: 'var(--text-tertiary)' }}>加载中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            欢迎回来
          </h1>
          <p style={{ color: 'var(--text-tertiary)', marginTop: '0.25rem' }}>
            这是你的管理后台概览
          </p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard 
          label="总书籍数" 
          value={perf?.books ?? '-'} 
          icon={BookOpen}
          color="var(--accent)"
        />
        <StatCard 
          label="总章节数" 
          value={perf?.chapters ?? '-'} 
          icon={FileText}
          color="var(--success)"
        />
        <StatCard 
          label="用户数" 
          value={perf?.users ?? '-'} 
          icon={Users}
          color="var(--info)"
        />
        <StatCard 
          label="标签数" 
          value={perf?.tags ?? '-'} 
          icon={Tags}
          color="var(--warning)"
        />
      </div>

      {/* System Health */}
      {health && (
        <div className="glass-card">
          <div className="flex items-center gap-3 mb-6">
            <Activity size={20} style={{ color: 'var(--text-secondary)' }} />
            <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
              系统健康
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <HealthItem label="数据库" ok={health.database} />
            <HealthItem label="缓存" ok={health.cache} />
            <HealthItem 
              label="系统状态" 
              ok={health.status === 'healthy' || health.status === 'ok'}
            />
          </div>
        </div>
      )}
    </div>
  );
}