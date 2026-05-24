import { useNavigate } from 'react-router-dom'
import { ShieldAlert, FileQuestion, ServerCrash, ArrowLeft, Home } from 'lucide-react'

interface ErrorPageProps {
  code: 403 | 404 | 500
  title?: string
  message?: string
}

const errorConfig = {
  403: {
    icon: ShieldAlert,
    defaultTitle: '拒绝访问',
    defaultMessage: '您没有权限访问此页面，请联系管理员获取权限。',
    color: 'text-warning',
    bgColor: 'bg-warning/10',
    borderColor: 'border-warning/20',
  },
  404: {
    icon: FileQuestion,
    defaultTitle: '页面未找到',
    defaultMessage: '您访问的页面不存在或已被移除。',
    color: 'text-info',
    bgColor: 'bg-info/10',
    borderColor: 'border-info/20',
  },
  500: {
    icon: ServerCrash,
    defaultTitle: '服务器错误',
    defaultMessage: '服务器遇到了意外错误，请稍后重试。',
    color: 'text-danger',
    bgColor: 'bg-danger/10',
    borderColor: 'border-danger/20',
  },
}

export default function ErrorPage({ code, title, message }: ErrorPageProps) {
  const navigate = useNavigate()
  const config = errorConfig[code]
  const Icon = config.icon

  return (
    <div className="min-h-screen flex items-center justify-center bg-content-bg p-6">
      <div className="max-w-lg w-full text-center">
        <div className={`w-24 h-24 mx-auto rounded-2xl ${config.bgColor} border ${config.borderColor} flex items-center justify-center mb-8`}>
          <Icon className={`w-12 h-12 ${config.color}`} />
        </div>

        <h1 className={`text-7xl font-bold ${config.color} mb-4 tracking-tight`}>
          {code}
        </h1>

        <h2 className="text-2xl font-semibold text-text-primary mb-3">
          {title || config.defaultTitle}
        </h2>

        <p className="text-text-secondary mb-8 leading-relaxed">
          {message || config.defaultMessage}
        </p>

        <div className="flex items-center justify-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 px-5 h-11 rounded-lg bg-card-bg border border-card-border text-text-primary hover:bg-white/[0.03] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            返回上一页
          </button>
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 px-5 h-11 rounded-lg bg-primary-500 text-white hover:bg-primary-600 transition-colors"
          >
            <Home className="w-4 h-4" />
            回到首页
          </button>
        </div>
      </div>
    </div>
  )
}
