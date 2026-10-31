import { AlertTriangle, RotateCcw } from 'lucide-react'
import { Component } from 'react'

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center min-h-screen p-8 bg-[#030305] text-white">
          <div className="flex flex-col items-center w-full max-w-2xl p-8 rounded-2xl border border-white/10 bg-white/[0.03]">
            <AlertTriangle
              size={48}
              className="text-red-400 mb-6 flex-shrink-0"
            />
            <h2 className="text-xl mb-4 font-semibold">An unexpected error occurred.</h2>
            <div className="p-4 w-full rounded-xl bg-black/40 overflow-auto mb-6 text-sm text-white/70">
              <pre className="whitespace-break-spaces">
                {this.state.error?.stack || this.state.error?.message}
              </pre>
            </div>
            <button
              onClick={() => window.location.reload()}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 text-white hover:bg-indigo-500 cursor-pointer font-medium"
            >
              <RotateCcw size={16} />
              Reload Page
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export default ErrorBoundary
