import { useState } from "react";
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
  DesktopRegular,
  ServerRegular,
  PeopleRegular,
  CheckmarkCircleRegular,
} from "@fluentui/react-icons";
import type {
  AvdQuestionResponse,
  AvdSkuResponse,
  AvdReferenceArchResponse,
} from "../../services/api";

export interface AvdAcceleratorPanelProps {
  questions: AvdQuestionResponse[];
  skus: AvdSkuResponse[];
  referenceArchitectures: AvdReferenceArchResponse[];
  loading?: boolean;
  error?: string | null;
  onQuestionAnswer?: (questionId: string, value: string) => void;
  onSkuSelect?: (skuName: string) => void;
  onReferenceSelect?: (refId: string) => void;
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
  description: {
    color: tokens.colorNeutralForeground2,
    fontSize: tokens.fontSizeBase200,
  },
  questionsGrid: {
    display: "grid",
    gridTemplateColumns: "1fr",
    gap: tokens.spacingVerticalS,
  },
  refGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
    gap: tokens.spacingVerticalS,
  },
  refCard: {
    cursor: "pointer",
    padding: tokens.spacingVerticalS,
    borderRadius: tokens.borderRadiusMedium,
    "&:hover": {
      backgroundColor: tokens.colorNeutralBackground1Hover,
    },
  },
  refCardSelected: {
    cursor: "pointer",
    padding: tokens.spacingVerticalS,
    borderRadius: tokens.borderRadiusMedium,
    backgroundColor: tokens.colorBrandBackground2,
    borderTopColor: tokens.colorBrandStroke1,
    borderRightColor: tokens.colorBrandStroke1,
    borderBottomColor: tokens.colorBrandStroke1,
    borderLeftColor: tokens.colorBrandStroke1,
  },
  badge: {
    marginLeft: tokens.spacingHorizontalXS,
  },
  skuInfo: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
  },
});

const AvdAcceleratorPanel: React.FC<AvdAcceleratorPanelProps> = ({
  questions,
  skus,
  referenceArchitectures,
  loading = false,
  error = null,
  onQuestionAnswer,
  onSkuSelect,
  onReferenceSelect,
  onGenerate,
}) => {
  const styles = useStyles();
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [selectedRef, setSelectedRef] = useState<string>("");
  const [selectedSku, setSelectedSku] = useState<string>("");

  const handleAnswer = (questionId: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
    onQuestionAnswer?.(questionId, value);
  };

  const handleSkuSelect = (skuName: string) => {
    setSelectedSku(skuName);
    onSkuSelect?.(skuName);
  };

  const handleRefSelect = (refId: string) => {
    setSelectedRef(refId);
    onReferenceSelect?.(refId);
  };

  const handleGenerate = () => {
    onGenerate?.(answers);
  };

  if (loading) {
    return (
      <div data-testid="avd-loading" className={styles.container}>
        <Spinner label="Loading AVD accelerator..." />
      </div>
    );
  }

  if (error) {
    return (
      <div data-testid="avd-error" className={styles.container}>
        <MessageBar intent="error">
          <MessageBarBody>{error}</MessageBarBody>
        </MessageBar>
      </div>
    );
  }

  return (
    <div data-testid="avd-panel" className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <DesktopRegular fontSize={24} />
        <Text size={500} weight="semibold">
          Azure Virtual Desktop Accelerator
        </Text>
      </div>

      <Text className={styles.description}>
        Configure your Azure Virtual Desktop landing zone. Answer the
        questions below to generate an optimised architecture with host pool
        sizing, FSLogix storage, and networking.
      </Text>

      {/* Reference Architectures */}
      <div className={styles.section}>
        <Text className={styles.sectionTitle}>
          <PeopleRegular /> Reference Architectures
        </Text>
        <div className={styles.refGrid}>
          {referenceArchitectures.map((ref) => (
            <Card
              key={ref.id}
              data-testid={`avd-ref-${ref.id}`}
              className={
                selectedRef === ref.id
                  ? styles.refCardSelected
                  : styles.refCard
              }
              onClick={() => handleRefSelect(ref.id)}
            >
              <CardHeader
                header={
                  <Text weight="semibold">
                    {ref.name}
                    <Badge
                      appearance="outline"
                      size="small"
                      className={styles.badge}
                    >
                      {ref.host_pool_type}
                    </Badge>
                  </Text>
                }
                description={
                  <Text className={styles.description}>
                    {ref.description}
                  </Text>
                }
              />
            </Card>
          ))}
        </div>
      </div>

      {/* Questionnaire */}
      <div className={styles.section}>
        <Text className={styles.sectionTitle}>Configuration Questions</Text>
        <div className={styles.questionsGrid}>
          {questions.map((q) => (
            <div key={q.id}>
              <Text>{q.text}</Text>
              <Dropdown
                data-testid={`avd-q-${q.id}`}
                placeholder="Select an option"
                value={answers[q.id] ?? ""}
                onOptionSelect={(_e, data) =>
                  handleAnswer(q.id, data.optionValue as string)
                }
              >
                {q.options.map((opt) => (
                  <Option key={opt.value} value={opt.value}>
                    {opt.label}
                  </Option>
                ))}
              </Dropdown>
            </div>
          ))}
        </div>
      </div>

      {/* SKU Picker */}
      {skus.length > 0 && (
        <div className={styles.section}>
          <Text className={styles.sectionTitle}>
            <ServerRegular /> Recommended VM SKUs
          </Text>
          <Dropdown
            data-testid="avd-sku-dropdown"
            placeholder="Select a VM SKU"
            value={selectedSku}
            onOptionSelect={(_e, data) =>
              handleSkuSelect(data.optionValue as string)
            }
          >
            {skus.map((sku) => (
              <Option key={sku.name} value={sku.name}>
                {sku.name} — {sku.vcpus} vCPUs, {sku.memory_gb} GiB
                {sku.gpu ? " (GPU)" : ""}
              </Option>
            ))}
          </Dropdown>
        </div>
      )}

      {/* Selected Reference Details */}
      {selectedRef && (
        <div className={styles.section}>
          <Text className={styles.sectionTitle}>
            <CheckmarkCircleRegular /> Components
          </Text>
          <ul>
            {referenceArchitectures
              .find((r) => r.id === selectedRef)
              ?.components.map((c, idx) => (
                <li key={idx}>
                  <Text size={200}>{c}</Text>
                </li>
              ))}
          </ul>
        </div>
      )}

      {/* Generate Button */}
      <Button
        appearance="primary"
        data-testid="avd-generate-button"
        disabled={Object.keys(answers).length === 0 && !selectedRef}
        onClick={handleGenerate}
      >
        Generate AVD Architecture
      </Button>
    </div>
  );
};

export default AvdAcceleratorPanel;
