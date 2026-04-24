import {
  makeStyles,
  tokens,
  MessageBar,
  MessageBarBody,
  MessageBarTitle,
  Button,
} from "@fluentui/react-components";
import { ArrowClockwiseRegular } from "@fluentui/react-icons";

const useErrorStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: tokens.spacingVerticalL,
    paddingTop: tokens.spacingVerticalXXL,
    paddingLeft: tokens.spacingHorizontalXXL,
    paddingRight: tokens.spacingHorizontalXXL,
    paddingBottom: tokens.spacingHorizontalXXL,
  },
  messageBar: {
    maxWidth: "600px",
    width: "100%",
  },
});

interface PageErrorFallbackProps {
  pageName?: string;
  error: Error | null;
  onRetry: () => void;
}

export default function PageErrorFallback({
  pageName,
  error,
  onRetry,
}: PageErrorFallbackProps) {
  const styles = useErrorStyles();
  const title = pageName ? `Error in ${pageName}` : "Something went wrong";

  return (
    <div className={styles.container} data-testid="page-error-boundary">
      <div className={styles.messageBar}>
        <MessageBar intent="error">
          <MessageBarBody>
            <MessageBarTitle>{title}</MessageBarTitle>
            {error?.message ||
              "An unexpected error occurred. Please try again."}
          </MessageBarBody>
        </MessageBar>
      </div>
      <Button
        appearance="primary"
        icon={<ArrowClockwiseRegular />}
        onClick={onRetry}
      >
        Retry
      </Button>
    </div>
  );
}
