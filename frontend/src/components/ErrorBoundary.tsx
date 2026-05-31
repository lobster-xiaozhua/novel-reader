import { Component, ReactNode } from 'react'
import { AlertTriangle, RefreshCw, Copy, Terminal, ChevronDown, ChevronUp } from 'lucide-react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
  showDetails: boolean
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null, showDetails: false }
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error, showDetails: false }
  }

  private copyErrorToClipboard = () => {
    const { error } = this.state
    if (!error) return
    const text = `${error.name}: ${error.message}\n${error.stack || ''}`
    navigator.clipboard.writeText(text).catch(() => {})
  }

  private renderErrorDetails() {
    const { error, showDetails } = this.state
    if (!error) return null

    const isDev = import.meta.env?.DEV ?? false

    return (
      <div className="mt-6 text-left">
        <button
          onClick={() => this.setState(s => ({ showDetails: !s.showDetails }))}
          className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary transition-colors"
        >
          <Terminal className="w-4 h-4" />
          {showDetails ? '收起' : '展开'}错误详情
          {showDetails ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>

        {showDetails && (
          <div className="mt-3 p-4 rounded-xl bg-black/40 border border-white/10 font-mono text-xs overflow-auto max-h-64">
            <div className="space-y-2">
              <div>
                <span className="text-danger font-semibold">错误类型:</span>{' '}
                <span className="text-text-secondary">{error.name}</span>
              </div>
              <div>
                <span className="text-danger font-semibold">错误信息:</span>{' '}
                <span className="text-warning">{error.message}</span>
              </div>
              {isDev && error.stack && (
                <div>
                  <span className="text-danger font-semibold">堆栈跟踪:</span>
                  <pre className="mt-2 text-text-muted whitespace-pre-wrap break-all">
                    {error.stack}
                  </pre>
                </div>
              )}
              {!isDev && (
                <div className="text-text-muted mt-2">
                  生产模式下堆栈已隐藏。请检查控制台日志。
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    )
  }

  render() {
    if (this.state.hasError) {
      const { error } = this.state

      const getSuggestion = (err: Error | null) => {
        if (!err) return '发生了未知错误，请尝试重新加载页面。'
        if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError'))
          return '网络连接异常。请检查网络设置或稍后重试。'
        if (err.message.includes('Cannot read') || err.message.includes('undefined'))
          return '数据加载异常。可能是组件渲染时缺少必要数据，请刷新重试。'
        if (err.message.includes('Invalid') || err.message.includes('Syntax'))
          return '数据格式异常。请联系技术支持或清除浏览器缓存后重试。'
        return '页面运行时发生错误，请尝试刷新页面。'
      }

      return (
        <div className="h-full flex items-center justify-center p-8 bg-content-bg">
          <div className="text-center max-w-lg w-full">
            <div className="w-20 h-20 mx-auto rounded-2xl bg-danger/10 border border-danger/20 flex items-center justify-center mb-6 animate-pulse">
              <AlertTriangle className="w-10 h-10 text-danger" />
            </div>

            <h2 className="text-2xl font-bold text-text-primary mb-2">页面运行时出错</h2>
            <p className="text-text-secondary mb-2">{getSuggestion(error)}</p>

            {error && (
              <div className="mt-4 px-4 py-3 rounded-lg bg-danger/5 border border-danger/10">
                <p className="text-sm font-medium text-danger truncate">
                  {error.name}: {error.message}
                </p>
              </div>
            )}

            {this.renderErrorDetails()}

            <div className="flex items-center justify-center gap-3 mt-6">
              <button
                onClick={this.copyErrorToClipboard}
                className="inline-flex items-center gap-2 px-4 h-10 rounded-lg bg-white/5 border border-white/10 text-text-secondary text-sm hover:bg-white/10 transition-colors"
              >
                <Copy className="w-4 h-4" />
                复制错误信息
              </button>
              <button
                onClick={() => { this.setState({ hasError: false, error: null, showDetails: false }); window.location.reload() }}
                className="inline-flex items-center gap-2 px-4 h-10 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-600 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                重新加载
              </button>
              <button
                onClick={() => this.setState({ hasError: false, error: null, showDetails: false })}
                className="inline-flex items-center gap-2 px-4 h-10 rounded-lg bg-white/5 border border-white/10 text-text-secondary text-sm hover:bg-white/10 transition-colors"
              >
                忽略并继续
              </button>
            </div>

            {import.meta.env?.DEV && (
              <p className="mt-6 text-xs text-text-muted">
                开发模式 · 错误已记录到控制台
              </p>
            )}
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
