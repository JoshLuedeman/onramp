import { ProgressBar as FluentProgressBar, Text, makeStyles, tokens } from "@fluentui/react-components";
import type { Progress } from "../../services/api";

const useStyles = makeStyles({
  container: {
    maxWidth: "640px",
    width: "100%",
    marginBottom: "24px",
  },
  label: {
    display: "flex",
    justifyContent: "space-between",
    marginBottom: "4px",
  },
  text: {
    color: tokens.colorNeutralForeground3,
    fontSize: tokens.fontSizeBase200,
  },
});

interface ProgressBarProps {
  progress: Progress;
}

export default function WizardProgressBar({ progress }: ProgressBarProps) {
  const styles = useStyles();
  return (
    <div className={styles.container}>
      <div className={styles.label}>
        <Text className={styles.text}>
          Question {progress.answered + 1} of {progress.total}
        </Text>
        <Text className={styles.text}>{progress.percent_complete}% complete</Text>
      </div>
      <FluentProgressBar value={progress.percent_complete / 100} thickness="large" color="brand" />
    </div>
  );
}
