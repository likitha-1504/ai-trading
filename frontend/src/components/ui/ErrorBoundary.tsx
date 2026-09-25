import { Component, ErrorInfo, ReactNode } from "react";
import { AlertOctagon, RotateCcw } from "lucide-react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#0B0E14] text-[#F1F5F9] flex flex-col items-center justify-center p-6">
          <div className="max-w-lg w-full p-6 rounded-lg bg-[#151A23] border border-rose-800/80 shadow-[0_0_30px_rgba(225,29,72,0.15)] text-center space-y-4">
            <div className="w-12 h-12 rounded-full bg-rose-950 flex items-center justify-center mx-auto border border-rose-600 text-rose-400">
              <AlertOctagon size={24} />
            </div>
            <div>
              <h2 className="text-base font-bold font-mono text-slate-100 uppercase tracking-wider">
                Terminal Render Invariant Guard
              </h2>
              <p className="text-xs text-rose-300 font-mono mt-1">
                {this.state.error?.message || "An unexpected UI error occurred."}
              </p>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              The trading terminal caught an unhandled rendering error. Position Watcher and deterministic core continue running safely in the background.
            </p>
            <div className="pt-2">
              <button
                onClick={() => {
                  this.setState({ hasError: false, error: null });
                  window.location.reload();
                }}
                className="inline-flex items-center gap-2 px-4 py-2 rounded bg-sky-600 text-white font-mono text-xs font-bold hover:bg-sky-500 transition-colors shadow-sm"
              >
                <RotateCcw size={14} />
                Reload Terminal
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
