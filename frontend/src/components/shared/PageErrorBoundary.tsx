import { Component, type ReactNode } from "react";
import PageErrorFallback from "./PageErrorFallback";

interface Props {
  children: ReactNode;
  pageName?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Page-level error boundary that catches errors within a single page,
 * preventing the entire app from crashing. Uses a functional fallback
 * component so Griffel's makeStyles hook can be used for styling.
 *
 * NOTE: Error boundaries must be class components (React limitation).
 */
export default class PageErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  private handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <PageErrorFallback
          pageName={this.props.pageName}
          error={this.state.error}
          onRetry={this.handleRetry}
        />
      );
    }
    return this.props.children;
  }
}
