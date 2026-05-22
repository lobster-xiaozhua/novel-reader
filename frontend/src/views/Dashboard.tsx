import { useQuery } from '@tanstack/react-query'
import {
  BookOpen,
  Clock,
  FileText,
  Type,
  Bug,
  CheckCircle,
  AlertTriangle,
} from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { fetchStats } from '@/api/stats'
import { fetchCrawlerTasks } from '@/api/crawler'
import { CHART_COLORS, COLORS } from '@/config/colors'

export default function Dashboard() {
  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: () => fetchStats(7),
  })

  const { data: crawlerData } = useQuery({
    queryKey: ['crawler-tasks'],
    queryFn: () => fetchCrawlerTasks(),
  })

  const cards = [
    { title: '总书籍数', value: stats?.total_books || 0, icon: BookOpen, color: 'text-primary-500', bg: 'bg-primary-500/10' },
    { title: '今日阅读', value: `${stats?.today_minutes || 0}分钟`, icon: Clock, color: 'text-warning', bg: 'bg-warning/10' },
    { title: '今日章节', value: stats?.today_chapters || 0, icon: FileText, color: 'text-success', bg: 'bg-success/10' },
    { title: '今日字数', value: `${Math.floor((stats?.total_words || 0) / 1000)}k`, icon: Type, color: 'text-info', bg: 'bg-info/10' },
    { title: '爬虫等待中', value: crawlerData?.items?.filter((t) => t.status === 'pending').length || 0, icon: Bug, color: 'text-warning', bg: 'bg-warning/10' },
    { title: '爬虫已完成', value: crawlerData?.items?.filter((t) => t.status === 'completed').length || 0, icon: CheckCircle, color: 'text-success', bg: 'bg-success/10' },
    { title: '爬虫失败', value: crawlerData?.items?.filter((t) => t.status === 'failed').length || 0, icon: AlertTriangle, color: 'text-danger', bg: 'bg-danger/10' },
    { title: '本周章节', value: stats?.week_chapters || 0, icon: FileText, color: 'text-primary-500', bg: 'bg-primary-500/10' },
  ]

  const chartData = stats?.chart || []

  const categoryData = [
    { name: '玄幻', value: 3 },
    { name: '仙侠', value: 2 },
    { name: '都市', value: 1 },
    { name: '科幻', value: 1 },
    { name: '奇幻', value: 1 },
  ]

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {cards.map((card) => (
          <div
            key={card.title}
            className="bg-card-bg border border-card-border rounded-xl p-5 card-hover"
          >
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

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trend Chart */}
        <div className="bg-card-bg border border-card-border rounded-xl p-5">
          <h3 className="text-lg font-semibold text-text-primary mb-1">最近7天阅读趋势</h3>
          <p className="text-sm text-text-muted mb-4">
            本周累计阅读 {stats?.week_chapters || 0} 章节
          </p>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorMinutes" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorChapters" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="date" stroke="#64748b" fontSize={12} />
                <YAxis stroke="#64748b" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    background: '#1a2235',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '8px',
                    color: '#f1f5f9',
                  }}
                />
                <Area type="monotone" dataKey="minutes" stroke={COLORS.primary} fillOpacity={1} fill="url(#colorMinutes)" name="阅读分钟" />
                  <Area type="monotone" dataKey="chapters" stroke={COLORS.success} fillOpacity={1} fill="url(#colorChapters)" name="阅读章节" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Category Chart */}
        <div className="bg-card-bg border border-card-border rounded-xl p-5">
          <h3 className="text-lg font-semibold text-text-primary mb-4">书籍分类分布</h3>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={categoryData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {categoryData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: '#1a2235',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '8px',
                    color: '#f1f5f9',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap gap-4 justify-center mt-4">
            {categoryData.map((entry, index) => (
              <div key={entry.name} className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}
                />
                <span className="text-sm text-text-secondary">{entry.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
