import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { FolderOpen, Plus, Trash2, RefreshCw, Folder, FileText, CheckCircle, XCircle, AlertTriangle } from 'lucide-react'
import { fetchBookDirs, addBookDir, removeBookDir, scanBookDirs, type BookDirInfo } from '@/api/books'
import { Spinner } from '@/components/Loading'

export default function BookDirs() {
  const qc = useQueryClient()
  const [newPath, setNewPath] = useState('')
  const [msg, setMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['book-dirs'],
    queryFn: fetchBookDirs,
  })

  const addMut = useMutation({
    mutationFn: addBookDir,
    onSuccess: (res: any) => {
      if (res.success) {
        setMsg({ type: 'ok', text: res.message || '添加成功' })
        setNewPath('')
        qc.invalidateQueries({ queryKey: ['book-dirs'] })
      } else {
        setMsg({ type: 'err', text: res.error || '添加失败' })
      }
    },
    onError: (e: any) => setMsg({ type: 'err', text: e.message || '添加失败' }),
  })

  const removeMut = useMutation({
    mutationFn: removeBookDir,
    onSuccess: (res: any) => {
      if (res.success) {
        setMsg({ type: 'ok', text: res.message || '已移除' })
        qc.invalidateQueries({ queryKey: ['book-dirs'] })
      } else {
        setMsg({ type: 'err', text: res.error || '移除失败' })
      }
    },
    onError: (e: any) => setMsg({ type: 'err', text: e.message || '移除失败' }),
  })

  const scanMut = useMutation({
    mutationFn: scanBookDirs,
    onSuccess: (res: any) => {
      const { imported = 0, errors = [] } = res
      if (imported > 0) {
        setMsg({ type: 'ok', text: `扫描完成：发现 ${imported} 本新书${errors.length ? `，${errors.length} 个错误` : ''}` })
        qc.invalidateQueries({ queryKey: ['book-dirs'] })
        qc.invalidateQueries({ queryKey: ['books'] })
      } else {
        setMsg({ type: 'ok', text: '扫描完成：没有发现新书' })
      }
    },
    onError: (e: any) => setMsg({ type: 'err', text: e.message || '扫描失败' }),
  })

  const dirs: BookDirInfo[] = data?.dirs || []

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl glass-card--compact flex items-center justify-center">
          <FolderOpen className="w-5 h-5 text-accent" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-text-primary">书籍目录管理</h1>
          <p className="text-sm text-text-muted">添加外挂目录后，点击「扫描入库」自动发现并导入新书</p>
        </div>
      </div>

      {/* Message */}
      {msg && (
        <div className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm glass-card ${
          msg.type === 'ok' ? 'border-success/30' : 'border-danger/30'
        }`}>
          {msg.type === 'ok' ? <CheckCircle className="w-4 h-4 text-success shrink-0" /> : <AlertTriangle className="w-4 h-4 text-danger shrink-0" />}
          <span className="flex-1">{msg.text}</span>
          <button onClick={() => setMsg(null)} className="text-text-muted hover:text-text-primary transition-colors">&times;</button>
        </div>
      )}

      {/* Add dir */}
      <div className="glass-card p-5">
        <h2 className="text-sm font-semibold text-text-primary mb-3">添加外挂目录</h2>
        <div className="flex gap-3">
          <input
            type="text"
            value={newPath}
            onChange={(e) => setNewPath(e.target.value)}
            placeholder="输入绝对路径，如 /mnt/novels 或 /sdcard/books"
            className="flex-1 px-4 py-2.5 rounded-lg glass-input text-sm text-text-primary placeholder:text-text-muted"
            onKeyDown={(e) => e.key === 'Enter' && newPath.trim() && addMut.mutate(newPath.trim())}
          />
          <button
            onClick={() => newPath.trim() && addMut.mutate(newPath.trim())}
            disabled={!newPath.trim() || addMut.isPending}
            className="btn btn--primary btn--md"
          >
            {addMut.isPending ? <Spinner size="sm" /> : <Plus className="w-4 h-4" />}
            添加
          </button>
        </div>
        <p className="text-xs text-text-muted mt-2">支持多个目录，添加后可在下方管理。路径必须是服务器上的绝对路径。</p>
      </div>

      {/* Dir list */}
      <div className="glass-card overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border/50">
          <h2 className="text-sm font-semibold text-text-primary">已配置目录</h2>
          <button
            onClick={() => scanMut.mutate()}
            disabled={scanMut.isPending}
            className="btn btn--primary btn--sm"
          >
            {scanMut.isPending ? <Spinner size="sm" /> : <RefreshCw className="w-3.5 h-3.5" />}
            扫描入库
          </button>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12"><Spinner /></div>
        ) : dirs.length === 0 ? (
          <div className="py-12 text-center text-text-muted text-sm">暂无目录</div>
        ) : (
          <div className="divide-y divide-white/[0.04] stagger-in">
            {dirs.map((dir, idx) => (
              <DirCard key={dir.path} dir={dir} onRemove={() => removeMut.mutate(dir.path)} onScan={() => scanMut.mutate(dir.path)} scanning={scanMut.isPending} idx={idx} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function DirCard({ dir, onRemove, onScan, scanning, idx }: { dir: BookDirInfo; onRemove: () => void; onScan: () => void; scanning: boolean; idx: number }) {
  const [expanded, setExpanded] = useState(false)

  const statusIcon = !dir.exists ? (
    <XCircle className="w-4 h-4 text-danger" />
  ) : dir.accessible === false ? (
    <AlertTriangle className="w-4 h-4 text-warning" />
  ) : (
    <CheckCircle className="w-4 h-4 text-success" />
  )

  const statusText = !dir.exists ? '不存在' : dir.accessible === false ? '无权限' : '正常'

  return (
    <div className="px-5 py-4 hover:bg-accent/5 transition-colors" style={{ animationDelay: `${idx * 0.04}s` }}>
      <div className="flex items-start gap-3">
        <Folder className={`w-5 h-5 mt-0.5 ${dir.type === '主目录' ? 'text-accent' : 'text-info'}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              dir.type === '主目录' ? 'bg-accent/10 text-accent' : 'bg-info/10 text-info'
            }`}>{dir.type}</span>
            <span className="flex items-center gap-1 text-xs text-text-muted">
              {statusIcon} {statusText}
            </span>
            {dir.exists && dir.accessible !== false && (
              <span className="text-xs text-text-muted">
                <FileText className="w-3 h-3 inline -mt-0.5" /> {dir.file_count} 个文件
              </span>
            )}
          </div>
          <p className="text-sm font-mono text-text-primary break-all">{dir.path}</p>

          {dir.books.length > 0 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-info hover:text-info/80 mt-1 transition-colors"
            >
              {expanded ? '收起' : `展开 ${dir.books.length} 本书`}
            </button>
          )}

          {expanded && dir.books.length > 0 && (
            <div className="mt-2 pl-3 border-l-2 border-white/10 space-y-1">
              {dir.books.map((b) => (
                <div key={b.name} className="flex items-center gap-2 text-xs text-text-secondary">
                  <FileText className="w-3 h-3" />
                  <span>{b.name}</span>
                  <span className="text-text-muted">({b.chapters}章)</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {dir.type === '外挂目录' && (
          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={onScan}
              disabled={scanning}
              className="btn btn--tertiary btn--sm"
              title="扫描此目录"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={onRemove}
              className="btn btn--danger btn--sm"
              title="移除此目录"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
