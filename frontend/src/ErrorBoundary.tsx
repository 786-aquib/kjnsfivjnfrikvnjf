import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

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
    console.error('Unhandled UI Error caught by ErrorBoundary:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary" role="alert">
          <AlertTriangle size={36} color="#b27735" />
          <h1>Something went wrong</h1>
          <p>
            An unexpected error occurred while rendering the page:{' '}
            <strong>{this.state.error?.message || 'Unknown error'}</strong>
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
          >
            <RefreshCw size={14} style={{ marginRight: 6, verticalAlign: -2 }} />
            Reload application
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
