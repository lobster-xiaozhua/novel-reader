import { Component, ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-full flex items-center justify-center p-8">
          <div className="text-center max-w-md">
            <div className="w-16 h-16 mx-auto rounded-2xl bg-danger/10 border border-danger/20 flex items-center justify-center mb-4">
              <AlertTriangle className="w-8 h-8 text-danger" />
            </div>
            <h2 className="text-xl font-bold text-text-primary mb-2">页面出错了</h2>
            <p className="text-text-secondary mb-6 text-sm">{this.state.error?.message || '发生了未知错误'}</p>
            <button
              onClick={() => { this.setState({ hasError: false, error: null }); window.location.reload() }}
              className="inline-flex items-center gap-2 px-4 h-10 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-600 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              重新加载
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
