import { Component, type ErrorInfo, type ReactNode } from 'react'

/** Bắt lỗi render không lường trước để không hiện trang trắng. */
export class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('UI error:', error, info.componentStack)
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div role="alert" className="mx-auto max-w-lg p-10 text-center">
        <h1 className="text-xl font-bold text-red-700">Có lỗi không mong muốn</h1>
        <p className="mt-2 text-sm text-slate-600">{this.state.error.message}</p>
        <button className="mt-4 rounded-md bg-indigo-600 px-4 py-2 text-sm text-white" onClick={() => window.location.assign('/')}>
          Tải lại ứng dụng
        </button>
      </div>
    )
  }
}
