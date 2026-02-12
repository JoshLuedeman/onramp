import {
  Card,
  Title2,
  Body1,
  Button,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import { CheckmarkCircleRegular, ArrowRightRegular } from "@fluentui/react-icons";

const useStyles = makeStyles({
  card: {
    maxWidth: "640px",
    width: "100%",
    padding: "48px",
    textAlign: "center",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "16px",
  },
  icon: {
    fontSize: "64px",
    color: tokens.colorPaletteGreenForeground1,
  },
});

interface WizardCompleteProps {
  onGenerate: () => void;
  answeredCount: number;
}

export default function WizardComplete({ onGenerate, answeredCount }: WizardCompleteProps) {
  const styles = useStyles();
  return (
    <Card className={styles.card}>
      <CheckmarkCircleRegular className={styles.icon} />
      <Title2>Questionnaire Complete!</Title2>
      <Body1>
        You&apos;ve answered {answeredCount} questions across all Azure CAF design areas.
        Click below to generate your landing zone architecture.
      </Body1>
      <Button
        appearance="primary"
        icon={<ArrowRightRegular />}
        iconPosition="after"
        size="large"
        onClick={onGenerate}
      >
        Generate Architecture
      </Button>
    </Card>
  );
}
