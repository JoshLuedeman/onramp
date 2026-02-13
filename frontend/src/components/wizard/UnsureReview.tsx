import {
  Card,
  Title2,
  Body1,
  Caption1,
  Badge,
  Button,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import { CheckmarkRegular, ArrowRightRegular } from "@fluentui/react-icons";

const useStyles = makeStyles({
  container: {
    maxWidth: "640px",
    width: "100%",
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  header: {
    textAlign: "center",
    marginBottom: "8px",
  },
  card: {
    padding: "20px",
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  },
  cardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  questionId: {
    fontWeight: tokens.fontWeightSemibold,
    textTransform: "capitalize",
  },
  reason: {
    color: tokens.colorNeutralForeground3,
  },
  footer: {
    display: "flex",
    justifyContent: "center",
    marginTop: "8px",
  },
});

function formatQuestionId(id: string): string {
  return id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatValue(value: string | string[]): string {
  if (Array.isArray(value)) {
    return value.map((v) => formatQuestionId(v)).join(", ");
  }
  return formatQuestionId(value);
}

interface Recommendation {
  question_id: string;
  recommended_value: string | string[];
  reason: string;
}

interface UnsureReviewProps {
  recommendations: Recommendation[];
  onAccept: (resolvedAnswers: Record<string, string | string[]>) => void;
}

export default function UnsureReview({ recommendations, onAccept }: UnsureReviewProps) {
  const styles = useStyles();

  const handleContinue = () => {
    const resolved: Record<string, string | string[]> = {};
    for (const rec of recommendations) {
      resolved[rec.question_id] = rec.recommended_value;
    }
    onAccept(resolved);
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Title2>AI Recommendations</Title2>
        <Body1>
          You selected &quot;Not sure&quot; for {recommendations.length} question
          {recommendations.length !== 1 ? "s" : ""}. Here are the recommended defaults:
        </Body1>
      </div>

      {recommendations.map((rec) => (
        <Card key={rec.question_id} className={styles.card}>
          <div className={styles.cardHeader}>
            <span className={styles.questionId}>{formatQuestionId(rec.question_id)}</span>
            <Badge
              appearance="filled"
              color="success"
              icon={<CheckmarkRegular />}
            >
              Accept
            </Badge>
          </div>
          <Body1>
            Recommended: <strong>{formatValue(rec.recommended_value)}</strong>
          </Body1>
          <Caption1 className={styles.reason}>{rec.reason}</Caption1>
        </Card>
      ))}

      <div className={styles.footer}>
        <Button
          appearance="primary"
          icon={<ArrowRightRegular />}
          iconPosition="after"
          size="large"
          onClick={handleContinue}
        >
          Continue with Recommendations
        </Button>
      </div>
    </div>
  );
}
