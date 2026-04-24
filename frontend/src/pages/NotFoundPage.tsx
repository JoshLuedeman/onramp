import { makeStyles, tokens, Title1, Text, Button } from "@fluentui/react-components";
import { useNavigate } from "react-router-dom";
import { ArrowLeftRegular } from "@fluentui/react-icons";

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "60vh",
    gap: tokens.spacingVerticalXL,
    padding: tokens.spacingHorizontalXXL,
    textAlign: "center",
  },
  code: {
    fontSize: "72px",
    fontWeight: tokens.fontWeightBold,
    color: tokens.colorNeutralForeground3,
    lineHeight: "1",
  },
});

export default function NotFoundPage() {
  const styles = useStyles();
  const navigate = useNavigate();

  return (
    <div className={styles.container}>
      <div className={styles.code}>404</div>
      <Title1>Page Not Found</Title1>
      <Text size={400}>The page you&apos;re looking for doesn&apos;t exist or has been moved.</Text>
      <Button
        appearance="primary"
        icon={<ArrowLeftRegular />}
        onClick={() => navigate("/")}
      >
        Back to Dashboard
      </Button>
    </div>
  );
}
