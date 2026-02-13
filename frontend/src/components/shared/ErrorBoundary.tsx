import { Component, type ReactNode } from "react";
import { MessageBar, MessageBarBody, Button } from "@fluentui/react-components";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 24 }}>
          <MessageBar intent="error">
            <MessageBarBody>
              Something went wrong: {this.state.error?.message}
            </MessageBarBody>
          </MessageBar>
          <Button
            onClick={() => this.setState({ hasError: false, error: null })}
            style={{ marginTop: 8 }}
          >
            Try Again
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}
