import { Component, type ReactNode } from "react";
import {
  makeStyles,
  tokens,
  MessageBar,
  MessageBarBody,
  Button,
} from "@fluentui/react-components";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

const useErrorFallbackStyles = makeStyles({
  container: {
    paddingTop: tokens.spacingVerticalXXL,
    paddingRight: tokens.spacingHorizontalXXL,
    paddingBottom: tokens.spacingVerticalXXL,
    paddingLeft: tokens.spacingHorizontalXXL,
  },
  retryButton: {
    marginTop: tokens.spacingVerticalS,
  },
});

// eslint-disable-next-line react-refresh/only-export-components
function ErrorFallback({
  error,
  onRetry,
}: {
  error: Error | null;
  onRetry: () => void;
}) {
  const styles = useErrorFallbackStyles();
  return (
    <div className={styles.container}>
      <MessageBar intent="error">
        <MessageBarBody>
          Something went wrong: {error?.message}
        </MessageBarBody>
      </MessageBar>
      <Button onClick={onRetry} className={styles.retryButton}>
        Try Again
      </Button>
    </div>
  );
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <ErrorFallback
          error={this.state.error}
          onRetry={() => this.setState({ hasError: false, error: null })}
        />
      );
    }
    return this.props.children;
  }
}
