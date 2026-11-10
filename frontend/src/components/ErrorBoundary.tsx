import { Component, type ErrorInfo, type ReactNode } from 'react'

/** Catches unexpected render errors so the user never sees a blank page. */
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
      <div role="alert" className="mx-auto mt-16 max-w-lg border-2 border-alert">
        <div className="bg-alert px-3 py-1 text-white" style={{ fontSize: 10.5, letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 700 }}>
          /// Unexpected error
        </div>
        <div className="p-4">
          <p className="font-bold">{this.state.error.message}</p>
          <button className="btn mt-4" onClick={() => window.location.assign('/')}>
            Reload application
          </button>
        </div>
      </div>
    )
  }
}
