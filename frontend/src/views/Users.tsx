import { useQuery } from '@tanstack/react-query'
import { Users as UsersIcon, Shield, User, Clock } from 'lucide-react'
import { userApi } from '@/api'
import { UserItem } from '@/types'
import { Spinner } from '@/components/Loading'

export default function Users() {
  const { data, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: userApi.list,
  })

  const users = data?.items || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-text-primary">用户管理</h2>
        <div className="text-sm text-text-muted">共 {users.length} 位用户</div>
      </div>

      {isLoading ? <Spinner /> : users.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-text-muted">
          <UsersIcon className="w-12 h-12 mb-3 opacity-30" /><p>暂无用户数据</p>
        </div>
      ) : (
        <div className="bg-card-bg border border-card-border rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/[0.06]">
                <th className="px-6 py-4 text-left text-sm font-medium text-text-secondary">用户</th>
                <th className="px-6 py-4 text-left text-sm font-medium text-text-secondary">邮箱</th>
                <th className="px-6 py-4 text-left text-sm font-medium text-text-secondary">角色</th>
                <th className="px-6 py-4 text-left text-sm font-medium text-text-secondary">书籍数</th>
                <th className="px-6 py-4 text-left text-sm font-medium text-text-secondary">注册时间</th>
                <th className="px-6 py-4 text-left text-sm font-medium text-text-secondary">最后登录</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user: UserItem) => (
                <tr key={user.id} className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-full bg-primary-500/10 flex items-center justify-center">
                        <User className="w-4 h-4 text-primary-500" />
                      </div>
                      <span className="text-sm font-medium text-text-primary">{user.username}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-text-secondary">{user.email || '-'}</td>
                  <td className="px-6 py-4">
                    {user.is_staff ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-primary-500/10 text-primary-500 text-xs font-medium">
                        <Shield className="w-3 h-3" />管理员
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-white/5 text-text-secondary text-xs">
                        <User className="w-3 h-3" />普通用户
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-text-primary font-medium">{user.book_count}</td>
                  <td className="px-6 py-4 text-sm text-text-muted">{new Date(user.date_joined).toLocaleDateString('zh-CN')}</td>
                  <td className="px-6 py-4 text-sm text-text-muted flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />{user.last_login ? new Date(user.last_login).toLocaleDateString('zh-CN') : '从未'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
