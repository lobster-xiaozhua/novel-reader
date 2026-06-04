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
      {/* 标题 */}
      <div className="flex items-center gap-3">
        <FolderOpen className="w-7 h-7 text-amber-500" />
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">书籍目录管理</h1>
      </div>
      <p className="text-sm text-gray-500 dark:text-gray-400 -mt-4 ml-10">
        添加外挂目录后，点击「扫描入库」自动发现并导入新书
      </p>

      {/* 消息提示 */}
      {msg && (
        <div className={`flex items-center gap-2 px-4 py-3 rounded-lg text-sm ${
          msg.type === 'ok' ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300' : 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300'
        }`}>
          {msg.type === 'ok' ? <CheckCircle className="w-4 h-4 shrink-0" /> : <AlertTriangle className="w-4 h-4 shrink-0" />}
          <span>{msg.text}</span>
          <button onClick={() => setMsg(null)} className="ml-auto opacity-60 hover:opacity-100">&times;</button>
        </div>
      )}

      {/* 添加目录 */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">添加外挂目录</h2>
        <div className="flex gap-3">
          <input
            type="text"
            value={newPath}
            onChange={(e) => setNewPath(e.target.value)}
            placeholder="输入绝对路径，如 /mnt/novels 或 /sdcard/books"
            className="flex-1 px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-900 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-amber-500 focus:border-amber-500 outline-none"
            onKeyDown={(e) => e.key === 'Enter' && newPath.trim() && addMut.mutate(newPath.trim())}
          />
          <button
            onClick={() => newPath.trim() && addMut.mutate(newPath.trim())}
            disabled={!newPath.trim() || addMut.isPending}
            className="flex items-center gap-2 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
          >
            {addMut.isPending ? <Spinner size="sm" /> : <Plus className="w-4 h-4" />}
            添加
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-2">支持多个目录，添加后可在下方管理。路径必须是服务器上的绝对路径。</p>
      </div>

      {/* 目录列表 */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-700">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">已配置目录</h2>
          <button
            onClick={() => scanMut.mutate()}
            disabled={scanMut.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition-colors"
          >
            {scanMut.isPending ? <Spinner size="sm" /> : <RefreshCw className="w-3.5 h-3.5" />}
            扫描入库
          </button>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12"><Spinner /></div>
        ) : dirs.length === 0 ? (
          <div className="py-12 text-center text-gray-400 text-sm">暂无目录</div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-700">
            {dirs.map((dir) => (
              <DirCard key={dir.path} dir={dir} onRemove={() => removeMut.mutate(dir.path)} onScan={() => scanMut.mutate(dir.path)} scanning={scanMut.isPending} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function DirCard({ dir, onRemove, onScan, scanning }: { dir: BookDirInfo; onRemove: () => void; onScan: () => void; scanning: boolean }) {
  const [expanded, setExpanded] = useState(false)

  const statusIcon = !dir.exists ? (
    <XCircle className="w-4 h-4 text-red-500" />
  ) : dir.accessible === false ? (
    <AlertTriangle className="w-4 h-4 text-yellow-500" />
  ) : (
    <CheckCircle className="w-4 h-4 text-green-500" />
  )

  const statusText = !dir.exists ? '不存在' : dir.accessible === false ? '无权限' : '正常'

  return (
    <div className="px-5 py-4">
      <div className="flex items-start gap-3">
        <Folder className={`w-5 h-5 mt-0.5 ${dir.type === '主目录' ? 'text-amber-500' : 'text-blue-500'}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              dir.type === '主目录' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
            }`}>{dir.type}</span>
            <span className="flex items-center gap-1 text-xs text-gray-500">
              {statusIcon} {statusText}
            </span>
            {dir.exists && dir.accessible !== false && (
              <span className="text-xs text-gray-400">
                <FileText className="w-3 h-3 inline -mt-0.5" /> {dir.file_count} 个文件
              </span>
            )}
          </div>
          <p className="text-sm font-mono text-gray-700 dark:text-gray-300 break-all">{dir.path}</p>

          {/* 展开书籍列表 */}
          {dir.books.length > 0 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-blue-500 hover:text-blue-600 mt-1"
            >
              {expanded ? '收起' : `展开 ${dir.books.length} 本书`}
            </button>
          )}

          {expanded && dir.books.length > 0 && (
            <div className="mt-2 pl-3 border-l-2 border-gray-200 dark:border-gray-600 space-y-1">
              {dir.books.map((b) => (
                <div key={b.name} className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
                  <FileText className="w-3 h-3" />
                  <span>{b.name}</span>
                  <span className="text-gray-400">({b.chapters}章)</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 操作按钮 */}
        <div className="flex items-center gap-2 shrink-0">
          {dir.type === '外挂目录' && (
            <>
              <button
                onClick={onScan}
                disabled={scanning}
                className="p-2 text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                title="扫描此目录"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
              <button
                onClick={onRemove}
                className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                title="移除此目录"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
