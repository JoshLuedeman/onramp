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
  Divider,
} from "@fluentui/react-components";
import { ArrowRightRegular } from "@fluentui/react-icons";
import type { DiscoveredAnswer, Question } from "../../services/api";

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
  recommendedOption: {
    backgroundColor: "#FFF8E1",
    borderRadius: "6px",
    padding: "4px 8px",
    border: "1px solid #FFD54F",
  },
  unsureDivider: {
    marginTop: "12px",
    marginBottom: "4px",
  },
  unsureOption: {
    fontStyle: "italic",
    color: tokens.colorNeutralForeground3,
  },
  discoveredBanner: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "8px 12px",
    backgroundColor: tokens.colorNeutralBackground3,
    borderRadius: "6px",
    marginBottom: "12px",
  },
  discoveredText: {
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
  },
  fullWidthInput: {
    width: "100%",
  },
});

interface QuestionCardProps {
  question: Question;
  onAnswer: (questionId: string, answer: string | string[]) => void;
  existingAnswer?: string | string[];
  discoveredAnswer?: DiscoveredAnswer;
}

export default function QuestionCard({ question, onAnswer, existingAnswer, discoveredAnswer }: QuestionCardProps) {
  const styles = useStyles();
  const discovered = discoveredAnswer || question.discovered_answer;
  const initialValue = (existingAnswer as string) || (
    discovered ? String(discovered.value) : ""
  );
  const [textValue, setTextValue] = useState<string>(
    question.type === "text" ? initialValue : ""
  );
  const [selectedValue, setSelectedValue] = useState<string>(
    question.type === "single_choice" ? initialValue : ""
  );
  const [checkedValues, setCheckedValues] = useState<string[]>(
    (existingAnswer as string[]) || (
      discovered && Array.isArray(discovered.value)
        ? discovered.value as string[]
        : []
    )
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

  const regularOptions = question.options?.filter((o) => o.value !== "_unsure") || [];
  const unsureOption = question.options?.find((o) => o.value === "_unsure");

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

      {discovered && !existingAnswer && (
        <div className={styles.discoveredBanner}>
          <Badge appearance="filled" color="informative" size="small">
            Auto-discovered
          </Badge>
          <Text className={styles.discoveredText}>
            {discovered.evidence || "Pre-filled from environment scan"}
            {" — you can override this selection"}
          </Text>
        </div>
      )}

      {question.type === "text" && (
        <Input
          value={textValue}
          onChange={(_, data) => setTextValue(data.value)}
          placeholder="Type your answer..."
          size="large"
          className={styles.fullWidthInput}
        />
      )}

      {question.type === "single_choice" && question.options && (
        <RadioGroup value={selectedValue} onChange={(_, data) => setSelectedValue(data.value)}>
          {regularOptions.map((opt) => (
            <div key={opt.value} className={opt.recommended ? styles.recommendedOption : undefined}>
              <Radio
                value={opt.value}
                label={opt.recommended ? `${opt.label} (Recommended)` : opt.label}
              />
            </div>
          ))}
          {unsureOption && (
            <>
              <Divider className={styles.unsureDivider} />
              <div className={styles.unsureOption}>
                <Radio value={unsureOption.value} label={unsureOption.label} />
              </div>
            </>
          )}
        </RadioGroup>
      )}

      {question.type === "multi_choice" && question.options && (
        <div className={styles.checkboxGroup}>
          {regularOptions.map((opt) => (
            <div key={opt.value} className={opt.recommended ? styles.recommendedOption : undefined}>
              <Checkbox
                label={opt.recommended ? `${opt.label} (Recommended)` : opt.label}
                checked={checkedValues.includes(opt.value)}
                onChange={(_, data) => {
                  if (data.checked) {
                    setCheckedValues([...checkedValues, opt.value]);
                  } else {
                    setCheckedValues(checkedValues.filter((v) => v !== opt.value));
                  }
                }}
              />
            </div>
          ))}
          {unsureOption && (
            <>
              <Divider className={styles.unsureDivider} />
              <div className={styles.unsureOption}>
                <Checkbox
                  label={unsureOption.label}
                  checked={checkedValues.includes(unsureOption.value)}
                  onChange={(_, data) => {
                    if (data.checked) {
                      setCheckedValues([...checkedValues, unsureOption.value]);
                    } else {
                      setCheckedValues(checkedValues.filter((v) => v !== unsureOption.value));
                    }
                  }}
                />
              </div>
            </>
          )}
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
