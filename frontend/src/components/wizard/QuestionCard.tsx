import { useState } from "react";
import {
  Card,
  CardHeader,
  Text,
  RadioGroup,
  Radio,
  Checkbox,
  Input,
  Button,
  makeStyles,
  tokens,
  Badge,
} from "@fluentui/react-components";
import { ArrowRightRegular } from "@fluentui/react-icons";
import type { Question } from "../../services/api";

const useStyles = makeStyles({
  card: {
    maxWidth: "640px",
    width: "100%",
    padding: "24px",
  },
  questionText: {
    fontSize: tokens.fontSizeBase500,
    fontWeight: tokens.fontWeightSemibold,
    marginBottom: "16px",
  },
  helpText: {
    color: tokens.colorNeutralForeground3,
    marginBottom: "16px",
  },
  actions: {
    display: "flex",
    justifyContent: "flex-end",
    marginTop: "24px",
    gap: "8px",
  },
  badge: {
    marginBottom: "8px",
  },
  checkboxGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  },
});

interface QuestionCardProps {
  question: Question;
  onAnswer: (questionId: string, answer: string | string[]) => void;
  existingAnswer?: string | string[];
}

export default function QuestionCard({ question, onAnswer, existingAnswer }: QuestionCardProps) {
  const styles = useStyles();
  const [textValue, setTextValue] = useState<string>((existingAnswer as string) || "");
  const [selectedValue, setSelectedValue] = useState<string>((existingAnswer as string) || "");
  const [checkedValues, setCheckedValues] = useState<string[]>(
    (existingAnswer as string[]) || []
  );

  const handleSubmit = () => {
    if (question.type === "text") {
      onAnswer(question.id, textValue);
    } else if (question.type === "single_choice") {
      onAnswer(question.id, selectedValue);
    } else if (question.type === "multi_choice") {
      onAnswer(question.id, checkedValues);
    }
  };

  const isValid = () => {
    if (question.type === "text") return textValue.trim().length > 0;
    if (question.type === "single_choice") return selectedValue.length > 0;
    if (question.type === "multi_choice") return checkedValues.length > 0;
    return false;
  };

  const cafAreaLabels: Record<string, string> = {
    billing_tenant: "Billing & Tenant",
    identity_access: "Identity & Access",
    resource_organization: "Resource Organization",
    network_connectivity: "Network & Connectivity",
    security: "Security",
    management: "Management",
    governance: "Governance",
    platform_automation: "Platform Automation",
  };

  return (
    <Card className={styles.card}>
      <CardHeader
        header={
          <Badge className={styles.badge} appearance="outline" color="brand">
            {cafAreaLabels[question.caf_area] || question.caf_area}
          </Badge>
        }
      />
      <Text className={styles.questionText}>{question.text}</Text>

      {question.type === "text" && (
        <Input
          value={textValue}
          onChange={(_, data) => setTextValue(data.value)}
          placeholder="Type your answer..."
          size="large"
          style={{ width: "100%" }}
        />
      )}

      {question.type === "single_choice" && question.options && (
        <RadioGroup value={selectedValue} onChange={(_, data) => setSelectedValue(data.value)}>
          {question.options.map((opt) => (
            <Radio key={opt.value} value={opt.value} label={opt.label} />
          ))}
        </RadioGroup>
      )}

      {question.type === "multi_choice" && question.options && (
        <div className={styles.checkboxGroup}>
          {question.options.map((opt) => (
            <Checkbox
              key={opt.value}
              label={opt.label}
              checked={checkedValues.includes(opt.value)}
              onChange={(_, data) => {
                if (data.checked) {
                  setCheckedValues([...checkedValues, opt.value]);
                } else {
                  setCheckedValues(checkedValues.filter((v) => v !== opt.value));
                }
              }}
            />
          ))}
        </div>
      )}

      <div className={styles.actions}>
        <Button
          appearance="primary"
          icon={<ArrowRightRegular />}
          iconPosition="after"
          onClick={handleSubmit}
          disabled={!isValid()}
          size="large"
        >
          Next
        </Button>
      </div>
    </Card>
  );
}
