import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { TrendingUp, BookOpen, Clock, Type } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'
import { fetchStats } from '@/api/stats'
import { COLORS } from '@/config/colors'
import { Spinner } from '@/components/Loading'

const DAY_OPTIONS = [
  { label: '7天', value: 7 },
  { label: '30天', value: 30 },
  { label: '90天', value: 90 },
]

export default function Stats() {
  const [days, setDays] = useState(7)

  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats', days],
    queryFn: () => fetchStats(days),
  })

  const chartData = stats?.chart || []

  const summaryCards = [
    { title: '总阅读时长', value: `${Math.floor((stats?.total_words || 0) / 300)}小时`, icon: Clock, color: 'text-primary-500', bg: 'bg-primary-500/10' },
    { title: '本周章节', value: stats?.week_chapters || 0, icon: BookOpen, color: 'text-success', bg: 'bg-success/10' },
    { title: '总字数', value: `${Math.floor((stats?.total_words || 0) / 10000)}万`, icon: Type, color: 'text-info', bg: 'bg-info/10' },
    { title: '阅读书籍', value: stats?.reading_count || 0, icon: TrendingUp, color: 'text-warning', bg: 'bg-warning/10' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-text-primary">阅读统计</h2>
        <div className="flex items-center gap-2">
          {DAY_OPTIONS.map((opt) => (
            <button key={opt.value} onClick={() => setDays(opt.value)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${days === opt.value ? 'bg-primary-500 text-white' : 'bg-card-bg border border-card-border text-text-secondary hover:text-text-primary'}`}>
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 stagger-in">
        {summaryCards.map((card, idx) => (
          <div key={card.title} className="glass-card p-5" style={{ animationDelay: `${idx * 0.03}s` }}>
            <div className="flex items-center gap-4">
              <div className={`w-12 h-12 rounded-xl ${card.bg} flex items-center justify-center`}>
                <card.icon className={`w-6 h-6 ${card.color}`} />
              </div>
              <div>
                <div className="text-2xl font-bold text-text-primary">{card.value}</div>
                <div className="text-sm text-text-secondary">{card.title}</div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card p-5">
          <h3 className="text-lg font-semibold text-text-primary mb-1">阅读时长趋势</h3>
          <p className="text-sm text-text-muted mb-4">最近{days}天阅读分钟数</p>
          <div className="h-[300px]">
            {isLoading ? <div className="flex items-center justify-center h-full"><Spinner /></div> : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorMinutes2" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={COLORS.primary} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={COLORS.primary} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="date" stroke="#64748b" fontSize={12} tickFormatter={(v) => new Date(v).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })} />
                  <YAxis stroke="#64748b" fontSize={12} />
                  <Tooltip contentStyle={{ background: '#1a2235', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#f1f5f9' }} labelFormatter={(v) => new Date(v).toLocaleDateString('zh-CN')} />
                  <Area type="monotone" dataKey="minutes" stroke={COLORS.primary} fillOpacity={1} fill="url(#colorMinutes2)" name="阅读分钟" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="glass-card p-5">
          <h3 className="text-lg font-semibold text-text-primary mb-1">阅读章节统计</h3>
          <p className="text-sm text-text-muted mb-4">最近{days}天阅读章节数</p>
          <div className="h-[300px]">
            {isLoading ? <div className="flex items-center justify-center h-full"><Spinner /></div> : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="date" stroke="#64748b" fontSize={12} tickFormatter={(v) => new Date(v).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })} />
                  <YAxis stroke="#64748b" fontSize={12} />
                  <Tooltip contentStyle={{ background: '#1a2235', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#f1f5f9' }} labelFormatter={(v) => new Date(v).toLocaleDateString('zh-CN')} />
                  <Bar dataKey="chapters" fill={COLORS.success} radius={[4, 4, 0, 0]} name="阅读章节" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      <div className="glass-card p-5">
        <h3 className="text-lg font-semibold text-text-primary mb-1">阅读字数趋势</h3>
        <p className="text-sm text-text-muted mb-4">最近{days}天阅读字数</p>
        <div className="h-[300px]">
          {isLoading ? <div className="flex items-center justify-center h-full"><Spinner /></div> : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorWords" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={COLORS.info} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={COLORS.info} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="date" stroke="#64748b" fontSize={12} tickFormatter={(v) => new Date(v).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })} />
                <YAxis stroke="#64748b" fontSize={12} />
                <Tooltip contentStyle={{ background: '#1a2235', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#f1f5f9' }} labelFormatter={(v) => new Date(v).toLocaleDateString('zh-CN')} formatter={(value: number) => [`${value.toLocaleString()} 字`, '阅读字数']} />
                <Area type="monotone" dataKey="words" stroke={COLORS.info} fillOpacity={1} fill="url(#colorWords)" name="阅读字数" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  )
}
