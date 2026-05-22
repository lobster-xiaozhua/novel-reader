import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Tag, Plus, Search, Trash2, X, Check } from 'lucide-react'
import { fetchTags, createTag, deleteTag } from '@/api/tags'
import { TagItem } from '@/types'
import { useDialog } from '@/components/ReDialog'
import { useToast } from '@/components/Toast'
import { TAG_COLORS } from '@/config/colors'
import { Spinner } from '@/components/Loading'

export default function Tags() {
  const queryClient = useQueryClient()
  const dialog = useDialog()
  const toast = useToast()
  const [search, setSearch] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [newColor, setNewColor] = useState(TAG_COLORS[0])

  const { data, isLoading } = useQuery({
    queryKey: ['tags'],
    queryFn: fetchTags,
  })

  const createMutation = useMutation({
    mutationFn: createTag,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tags'] })
      setIsCreating(false)
      setNewName('')
      setNewColor(TAG_COLORS[0])
      toast.success('标签创建成功')
    },
    onError: () => toast.error('创建失败'),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteTag,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tags'] })
      toast.success('标签已删除')
    },
    onError: () => toast.error('删除失败'),
  })

  const tags = data?.items || []
  const filtered = search ? tags.filter((t: TagItem) => t.name.toLowerCase().includes(search.toLowerCase())) : tags

  const handleCreate = () => {
    if (!newName.trim()) return
    createMutation.mutate({ name: newName.trim(), color: newColor })
  }

  const handleDelete = async (tag: TagItem) => {
    const confirmed = await dialog.confirm({
      title: '删除标签',
      content: <p className="text-text-secondary">确定要删除标签 <span className="font-medium text-text-primary">「{tag.name}」</span> 吗？此操作不可撤销。</p>,
      confirmText: '删除',
      cancelText: '取消',
    })
    if (confirmed) deleteMutation.mutate(tag.id)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-text-primary">标签管理</h2>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            <input type="text" placeholder="搜索标签..." value={search} onChange={(e) => setSearch(e.target.value)}
              className="w-56 h-10 pl-9 pr-4 rounded-lg bg-card-bg border border-card-border text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-500/50 transition-colors" />
          </div>
          <button onClick={() => setIsCreating(true)} className="flex items-center gap-2 px-4 h-10 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-600 transition-colors">
            <Plus className="w-4 h-4" />新建标签
          </button>
        </div>
      </div>

      {isCreating && (
        <div className="bg-card-bg border border-card-border rounded-xl p-5">
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-text-secondary mb-1.5">标签名称</label>
              <input type="text" value={newName} onChange={(e) => setNewName(e.target.value)}
                className="w-full h-10 px-4 rounded-lg bg-content-bg border border-card-border text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-500/50 transition-colors"
                placeholder="输入标签名称" autoFocus />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1.5">颜色</label>
              <div className="flex items-center gap-2">
                {TAG_COLORS.map((c) => (
                  <button key={c} onClick={() => setNewColor(c)}
                    className={`w-7 h-7 rounded-full transition-transform ${newColor === c ? 'ring-2 ring-white scale-110' : ''}`}
                    style={{ backgroundColor: c }} />
                ))}
              </div>
            </div>
            <div className="flex items-end gap-2 pt-6">
              <button onClick={handleCreate} disabled={createMutation.isPending || !newName.trim()}
                className="flex items-center gap-1 px-4 h-10 rounded-lg bg-success text-white text-sm font-medium hover:bg-success/90 transition-colors disabled:opacity-50">
                <Check className="w-4 h-4" />确认
              </button>
              <button onClick={() => setIsCreating(false)}
                className="flex items-center gap-1 px-4 h-10 rounded-lg bg-white/5 text-text-secondary text-sm hover:bg-white/10 transition-colors">
                <X className="w-4 h-4" />取消
              </button>
            </div>
          </div>
        </div>
      )}

      {isLoading ? <Spinner /> : filtered.length === 0 ? (
        <div className="text-center py-20 text-text-muted">
          <Tag className="w-12 h-12 mx-auto mb-3 opacity-30" /><p>暂无标签</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {filtered.map((tag: TagItem) => (
            <div key={tag.id} className="bg-card-bg border border-card-border rounded-xl p-4 card-hover group">
              <div className="flex items-center justify-between mb-3">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium"
                  style={{ backgroundColor: `${tag.color}20`, color: tag.color }}>
                  <Tag className="w-3 h-3" />{tag.name}
                </span>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button onClick={() => handleDelete(tag)} className="p-1 rounded-md hover:bg-danger/10 text-text-muted hover:text-danger transition-colors">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
              <div className="text-2xl font-bold text-text-primary">{tag.book_count}</div>
              <div className="text-xs text-text-muted">关联书籍</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
