import { MessageBar, MessageBarBody, Button } from "@fluentui/react-components";

interface ApiErrorProps {
  message: string;
  onRetry?: () => void;
}

export default function ApiError({ message, onRetry }: ApiErrorProps) {
  return (
    <div style={{ margin: "16px 0" }}>
      <MessageBar intent="error">
        <MessageBarBody>{message}</MessageBarBody>
      </MessageBar>
      {onRetry && (
        <Button onClick={onRetry} style={{ marginTop: 8 }}>
          Retry
        </Button>
      )}
    </div>
  );
}
