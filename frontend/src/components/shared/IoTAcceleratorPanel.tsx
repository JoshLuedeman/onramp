import { useState, useMemo } from "react";
import {
  Card,
  CardHeader,
  Text,
  Badge,
  Button,
  Dropdown,
  Option,
  Spinner,
  MessageBar,
  MessageBarBody,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  PlugConnectedRegular,
  ServerRegular,
  CheckmarkCircleRegular,
} from "@fluentui/react-icons";
import type { IoTQuestion, IoTBestPractice } from "../../services/api";

export interface IoTAcceleratorPanelProps {
  questions: IoTQuestion[];
  bestPractices: IoTBestPractice[];
  loading?: boolean;
  error?: string | null;
  onAnswerChange?: (questionId: string, value: string) => void;
  onGenerate?: (answers: Record<string, string>) => void;
}

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalM,
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
  },
  section: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
  },
  sectionTitle: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase400,
  },
  questionsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
    gap: tokens.spacingVerticalS,
  },
  questionCard: {
    padding: tokens.spacingVerticalS,
    borderRadius: tokens.borderRadiusMedium,
  },
  description: {
    color: tokens.colorNeutralForeground2,
    fontSize: tokens.fontSizeBase200,
  },
  badge: {
    marginLeft: tokens.spacingHorizontalXS,
  },
  bestPracticeList: {
    margin: 0,
    paddingLeft: tokens.spacingHorizontalL,
  },
});

const IoTAcceleratorPanel: React.FC<IoTAcceleratorPanelProps> = ({
  questions,
  bestPractices,
  loading = false,
  error = null,
  onAnswerChange,
  onGenerate,
}) => {
  const styles = useStyles();
  const [answers, setAnswers] = useState<Record<string, string>>({});

  const answeredCount = useMemo(
    () => Object.keys(answers).length,
    [answers],
  );

  const handleAnswerChange = (questionId: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
    onAnswerChange?.(questionId, value);
  };

  const handleGenerate = () => {
    onGenerate?.(answers);
  };

  if (loading) {
    return (
      <div data-testid="iot-loading" className={styles.container}>
        <Spinner label="Loading IoT accelerator..." />
      </div>
    );
  }

  if (error) {
    return (
      <div data-testid="iot-error" className={styles.container}>
        <MessageBar intent="error">
          <MessageBarBody>{error}</MessageBarBody>
        </MessageBar>
      </div>
    );
  }

  return (
    <div data-testid="iot-panel" className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <PlugConnectedRegular fontSize={24} />
        <Text size={500} weight="semibold">
          IoT Landing Zone Accelerator
        </Text>
      </div>

      <Text className={styles.description}>
        Configure your Azure IoT landing zone by answering the questions below.
        The accelerator will recommend the right IoT Hub tier, architecture
        components, and infrastructure sizing for your deployment.
      </Text>

      {/* Questionnaire */}
      <div className={styles.section}>
        <Text className={styles.sectionTitle}>
          <ServerRegular /> IoT Configuration
          <Badge
            appearance="outline"
            size="small"
            className={styles.badge}
          >
            {answeredCount}/{questions.length}
          </Badge>
        </Text>
        <div className={styles.questionsGrid}>
          {questions.map((q) => (
            <Card
              key={q.id}
              data-testid={`iot-question-${q.id}`}
              className={styles.questionCard}
            >
              <CardHeader
                header={<Text weight="semibold">{q.text}</Text>}
                description={
                  <Text className={styles.description}>{q.help_text}</Text>
                }
              />
              <Dropdown
                data-testid={`iot-dropdown-${q.id}`}
                placeholder={`Select ${q.category}`}
                value={answers[q.id] ?? ""}
                onOptionSelect={(_e, data) =>
                  handleAnswerChange(q.id, data.optionValue as string)
                }
              >
                {q.options.map((opt) => (
                  <Option key={opt} value={opt}>
                    {opt}
                  </Option>
                ))}
              </Dropdown>
            </Card>
          ))}
        </div>
      </div>

      {/* Best Practices */}
      {bestPractices.length > 0 && (
        <div className={styles.section}>
          <Text className={styles.sectionTitle}>
            <CheckmarkCircleRegular /> Best Practices
          </Text>
          <ul className={styles.bestPracticeList}>
            {bestPractices.map((bp) => (
              <li key={bp.id}>
                <Text size={200}>
                  <strong>{bp.title}</strong> — {bp.description}
                </Text>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Generate Button */}
      <Button
        appearance="primary"
        data-testid="iot-generate-button"
        disabled={answeredCount === 0}
        onClick={handleGenerate}
      >
        Generate IoT Architecture
      </Button>
    </div>
  );
};

export default IoTAcceleratorPanel;
