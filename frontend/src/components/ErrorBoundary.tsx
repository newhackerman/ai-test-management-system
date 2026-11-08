import React from 'react'

interface ErrorBoundaryProps {
  children: React.ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

/**
 * 全站错误边界：任一路由渲染崩溃时不再白屏，而是显示可重试的兜底页。
 * 此前全站没有任何 error boundary（QueryErrorBoundary 只存在于已损坏
 * 的 QueryProvider.tsx 中，且无人引用），一次渲染异常就会卸载整个应用。
 */
class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    console.error('应用渲染异常:', error, info)
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null })
  }

  render(): React.ReactNode {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-background p-6">
          <div className="max-w-md w-full text-center space-y-4">
            <h1 className="text-xl font-semibold">页面加载出现问题</h1>
            <p className="text-sm text-muted-foreground">
              应用遇到了一个未预期的渲染错误。您可以重试，或刷新页面。
            </p>
            {this.state.error && (
              <p className="text-xs text-muted-foreground break-all">
                {this.state.error.message}
              </p>
            )}
            <button
              type="button"
              onClick={this.handleRetry}
              className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
            >
              重试
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export default ErrorBoundary
