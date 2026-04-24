import {
  makeStyles,
  tokens,
  MessageBar,
  MessageBarBody,
  Button,
} from "@fluentui/react-components";

const useStyles = makeStyles({
  container: {
    marginTop: tokens.spacingVerticalL,
    marginBottom: tokens.spacingVerticalL,
    marginLeft: "0",
    marginRight: "0",
  },
  retryButton: {
    marginTop: tokens.spacingVerticalS,
  },
});

interface ApiErrorProps {
  message: string;
  onRetry?: () => void;
}

export default function ApiError({ message, onRetry }: ApiErrorProps) {
  const styles = useStyles();
  return (
    <div className={styles.container}>
      <MessageBar intent="error">
        <MessageBarBody>{message}</MessageBarBody>
      </MessageBar>
      {onRetry && (
        <Button onClick={onRetry} className={styles.retryButton}>
          Retry
        </Button>
      )}
    </div>
  );
}
