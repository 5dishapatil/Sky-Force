import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  message: string;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, message: '' };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, message: error.message || 'An unexpected rendering error occurred.' };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('Sky Force view rendering failed:', error, info.componentStack);
  }

  private handleReset = () => {
    window.location.reload();
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <section className="render-error-panel" role="alert">
        <div className="render-error-icon"><AlertTriangle size={22} /></div>
        <div className="render-error-content">
          <p className="eyebrow">VIEW RENDERING ERROR</p>
          <h2>This view could not be displayed</h2>
          <p>This view failed while rendering. Use the sidebar to navigate elsewhere, or reload after checking the browser console for the component stack.</p>
          <code>{this.state.message}</code>
          <button className="button button-secondary" onClick={this.handleReset} type="button">
            <RefreshCw size={15} /> Reload application
          </button>
        </div>
      </section>
    );
  }
}
