import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Bug, Clock, CheckCircle, AlertTriangle, Loader2, XCircle, Plus } from 'lucide-react'
import { fetchCrawlerTasks, createCrawlerTask } from '@/api/crawler'
import { CrawlerTask } from '@/types'
import { useToast } from '@/components/Toast'
import { Spinner } from '@/components/Loading'

const statusConfig = {
  pending: { label: '等待中', icon: Clock, color: 'text-warning', bg: 'bg-warning/10' },
  running: { label: '运行中', icon: Loader2, color: 'text-info', bg: 'bg-info/10' },
  completed: { label: '已完成', icon: CheckCircle, color: 'text-success', bg: 'bg-success/10' },
  failed: { label: '失败', icon: AlertTriangle, color: 'text-danger', bg: 'bg-danger/10' },
  cancelled: { label: '已取消', icon: XCircle, color: 'text-text-muted', bg: 'bg-white/5' },
}

export default function Crawler() {
  const [url, setUrl] = useState('')
  const queryClient = useQueryClient()
  const toast = useToast()

  const { data, isLoading } = useQuery({
    queryKey: ['crawler-tasks'],
    queryFn: () => fetchCrawlerTasks(),
  })

  const createMutation = useMutation({
    mutationFn: createCrawlerTask,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crawler-tasks'] })
      setUrl('')
      toast.success('爬虫任务已创建')
    },
    onError: () => toast.error('创建任务失败'),
  })

  const tasks = data?.items || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-text-primary">爬虫任务</h2>
        <div className="flex items-center gap-3">
          <input type="text" placeholder="输入URL..." value={url} onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && url.trim() && createMutation.mutate(url.trim())}
            className="w-80 h-10 px-4 rounded-lg glass-input text-sm text-text-primary placeholder:text-text-muted" />
          <button onClick={() => { if (url.trim()) createMutation.mutate(url.trim()) }}
            disabled={createMutation.isPending || !url.trim()}
            className="btn btn--primary btn--md">
            {createMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            新建任务
          </button>
        </div>
      </div>

      <div className="grid grid-cols-5 gap-4">
        {Object.entries(statusConfig).map(([key, config], idx) => {
          const count = tasks.filter((t: CrawlerTask) => t.status === key).length
          const Icon = config.icon
          return (
            <div key={key} className="glass-card p-4 text-center" style={{ animationDelay: `${idx * 0.04}s` }}>
              <div className={`w-10 h-10 rounded-lg ${config.bg} flex items-center justify-center mx-auto`}>
                <Icon className={`w-5 h-5 ${config.color}`} />
              </div>
              <div className="text-2xl font-bold text-text-primary mt-2">{count}</div>
              <div className="text-sm text-text-secondary">{config.label}</div>
            </div>
          )
        })}
      </div>

      <div className="glass-card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/[0.06]">
              <th className="px-6 py-4 text-left text-sm font-medium text-text-secondary">URL</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-text-secondary">状态</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-text-secondary">进度</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-text-secondary">创建时间</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={4}><Spinner /></td></tr>
            ) : tasks.length === 0 ? (
              <tr><td colSpan={4} className="text-center py-20 text-text-muted">暂无爬虫任务</td></tr>
            ) : (
              tasks.map((task: CrawlerTask) => {
                const status = statusConfig[task.status]
                const StatusIcon = status.icon
                const progress = task.total_chapters > 0 ? Math.round((task.downloaded_chapters / task.total_chapters) * 100) : 0
                return (
                  <tr key={task.id} className="border-b border-white/[0.06] hover:bg-white/[0.02] transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <Bug className="w-4 h-4 text-text-muted" />
                        <span className="text-sm text-text-primary truncate max-w-md">{task.url}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md ${status.bg} ${status.color} text-xs font-medium`}>
                        <StatusIcon className={`w-3.5 h-3.5 ${task.status === 'running' ? 'animate-spin' : ''}`} />
                        {status.label}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-24 h-2 rounded-full bg-white/5 overflow-hidden">
                          <div className="h-full rounded-full bg-primary-500 transition-all" style={{ width: `${progress}%` }} />
                        </div>
                        <span className="text-sm text-text-secondary">{task.downloaded_chapters}/{task.total_chapters}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-text-muted">{new Date(task.created_at).toLocaleString('zh-CN')}</td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
