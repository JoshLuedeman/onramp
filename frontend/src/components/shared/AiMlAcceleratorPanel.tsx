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
  BrainCircuitRegular,
  ServerRegular,
  RocketRegular,
  CheckmarkCircleRegular,
} from "@fluentui/react-icons";
import type {
  AiMlGpuSku,
  AiMlReferenceArchitecture,
} from "../../services/api";

// ── Props ───────────────────────────────────────────────────────────────

export interface AiMlConfig {
  selectedGpu: string;
  selectedFramework: string;
  mlopsMaturity: string;
  selectedReferenceArch: string;
}

export interface AiMlAcceleratorPanelProps {
  gpuSkus: AiMlGpuSku[];
  referenceArchitectures: AiMlReferenceArchitecture[];
  loading?: boolean;
  error?: string | null;
  onGpuSelect?: (skuId: string) => void;
  onFrameworkSelect?: (framework: string) => void;
  onMlopsSelect?: (level: string) => void;
  onReferenceArchSelect?: (archId: string) => void;
  onApply?: (config: AiMlConfig) => void;
}

// ── Styles ──────────────────────────────────────────────────────────────

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
  archGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
    gap: tokens.spacingVerticalS,
  },
  archCard: {
    cursor: "pointer",
    padding: tokens.spacingVerticalS,
    borderRadius: tokens.borderRadiusMedium,
    "&:hover": {
      backgroundColor: tokens.colorNeutralBackground1Hover,
    },
  },
  archCardSelected: {
    cursor: "pointer",
    padding: tokens.spacingVerticalS,
    borderRadius: tokens.borderRadiusMedium,
    backgroundColor: tokens.colorBrandBackground2,
    borderTopColor: tokens.colorBrandStroke1,
    borderRightColor: tokens.colorBrandStroke1,
    borderBottomColor: tokens.colorBrandStroke1,
    borderLeftColor: tokens.colorBrandStroke1,
  },
  configRow: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalM,
  },
  serviceList: {
    margin: 0,
    paddingLeft: tokens.spacingHorizontalL,
    fontSize: tokens.fontSizeBase200,
  },
  badge: {
    marginLeft: tokens.spacingHorizontalXS,
  },
  footer: {
    display: "flex",
    justifyContent: "flex-end",
    gap: tokens.spacingHorizontalS,
    marginTop: tokens.spacingVerticalM,
  },
});

// ── Constants ───────────────────────────────────────────────────────────

const FRAMEWORKS = [
  { value: "pytorch", label: "PyTorch" },
  { value: "tensorflow", label: "TensorFlow" },
  { value: "onnx", label: "ONNX Runtime" },
  { value: "huggingface", label: "Hugging Face" },
  { value: "custom", label: "Custom / Other" },
];

const MLOPS_LEVELS = [
  { value: "ad_hoc", label: "Ad-hoc" },
  { value: "basic_cicd", label: "Basic CI/CD" },
  { value: "full_mlops", label: "Full MLOps" },
];

// ── Component ───────────────────────────────────────────────────────────

const AiMlAcceleratorPanel: React.FC<AiMlAcceleratorPanelProps> = ({
  gpuSkus,
  referenceArchitectures,
  loading = false,
  error = null,
  onGpuSelect,
  onFrameworkSelect,
  onMlopsSelect,
  onReferenceArchSelect,
  onApply,
}) => {
  const styles = useStyles();
  const [selectedGpu, setSelectedGpu] = useState<string>("");
  const [selectedFramework, setSelectedFramework] = useState<string>("");
  const [mlopsMaturity, setMlopsMaturity] = useState<string>("");
  const [selectedRefArch, setSelectedRefArch] = useState<string>("");

  const handleGpuSelect = (skuId: string) => {
    setSelectedGpu(skuId);
    onGpuSelect?.(skuId);
  };

  const handleFrameworkSelect = (value: string) => {
    setSelectedFramework(value);
    onFrameworkSelect?.(value);
  };

  const handleMlopsSelect = (value: string) => {
    setMlopsMaturity(value);
    onMlopsSelect?.(value);
  };

  const handleRefArchSelect = (archId: string) => {
    setSelectedRefArch(archId);
    onReferenceArchSelect?.(archId);
  };

  const handleApply = () => {
    onApply?.({
      selectedGpu,
      selectedFramework,
      mlopsMaturity,
      selectedReferenceArch: selectedRefArch,
    });
  };

  if (loading) {
    return (
      <div data-testid="aiml-loading" className={styles.container}>
        <Spinner label="Loading AI/ML accelerator options..." />
      </div>
    );
  }

  if (error) {
    return (
      <div data-testid="aiml-error" className={styles.container}>
        <MessageBar intent="error">
          <MessageBarBody>{error}</MessageBarBody>
        </MessageBar>
      </div>
    );
  }

  return (
    <div data-testid="aiml-panel" className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <BrainCircuitRegular fontSize={24} />
        <Text size={500} weight="semibold">
          AI/ML Landing Zone Accelerator
        </Text>
      </div>

      <Text className={styles.description}>
        Configure your Azure Machine Learning landing zone with GPU compute,
        MLOps pipelines and best-practice architecture patterns.
      </Text>

      {/* GPU Selector */}
      <div className={styles.section}>
        <Text className={styles.sectionTitle}>
          <ServerRegular /> GPU Compute
        </Text>
        <Dropdown
          data-testid="aiml-gpu-dropdown"
          placeholder="Select a GPU SKU"
          value={
            gpuSkus.find((s) => s.id === selectedGpu)?.name ?? ""
          }
          onOptionSelect={(_e, data) =>
            handleGpuSelect(data.optionValue as string)
          }
        >
          {gpuSkus.map((sku) => (
            <Option key={sku.id} value={sku.id} text={`${sku.name} (${sku.gpu_type} ×${sku.gpu_count}, ${sku.gpu_memory_gb} GB)`}>
              {sku.name} ({sku.gpu_type} ×{sku.gpu_count}, {sku.gpu_memory_gb}
              GB)
            </Option>
          ))}
        </Dropdown>
      </div>

      {/* Framework Picker */}
      <div className={styles.section}>
        <Text className={styles.sectionTitle}>ML Framework</Text>
        <Dropdown
          data-testid="aiml-framework-dropdown"
          placeholder="Select a framework"
          value={
            FRAMEWORKS.find((f) => f.value === selectedFramework)?.label ?? ""
          }
          onOptionSelect={(_e, data) =>
            handleFrameworkSelect(data.optionValue as string)
          }
        >
          {FRAMEWORKS.map((fw) => (
            <Option key={fw.value} value={fw.value} text={fw.label}>
              {fw.label}
            </Option>
          ))}
        </Dropdown>
      </div>

      {/* MLOps Maturity */}
      <div className={styles.section}>
        <Text className={styles.sectionTitle}>
          <RocketRegular /> MLOps Maturity
        </Text>
        <Dropdown
          data-testid="aiml-mlops-dropdown"
          placeholder="Select MLOps maturity level"
          value={
            MLOPS_LEVELS.find((l) => l.value === mlopsMaturity)?.label ?? ""
          }
          onOptionSelect={(_e, data) =>
            handleMlopsSelect(data.optionValue as string)
          }
        >
          {MLOPS_LEVELS.map((level) => (
            <Option key={level.value} value={level.value} text={level.label}>
              {level.label}
            </Option>
          ))}
        </Dropdown>
      </div>

      {/* Reference Architecture Cards */}
      <div className={styles.section}>
        <Text className={styles.sectionTitle}>Reference Architectures</Text>
        <div className={styles.archGrid}>
          {referenceArchitectures.map((arch) => (
            <Card
              key={arch.id}
              data-testid={`aiml-ref-arch-${arch.id}`}
              className={
                selectedRefArch === arch.id
                  ? styles.archCardSelected
                  : styles.archCard
              }
              onClick={() => handleRefArchSelect(arch.id)}
            >
              <CardHeader
                header={
                  <Text weight="semibold">
                    {arch.name}
                    <Badge
                      appearance="outline"
                      size="small"
                      className={styles.badge}
                    >
                      {arch.gpu_type}
                    </Badge>
                  </Text>
                }
                description={
                  <Text className={styles.description}>
                    {arch.description}
                  </Text>
                }
              />
              <Text className={styles.description}>
                Team size: {arch.team_size} · MLOps: {arch.mlops_level}
              </Text>
              <Text className={styles.description}>
                Est. ${arch.estimated_monthly_cost_usd.toLocaleString()}/mo
              </Text>
              {selectedRefArch === arch.id && (
                <ul className={styles.serviceList}>
                  {arch.services.map((svc) => (
                    <li key={svc}>{svc}</li>
                  ))}
                </ul>
              )}
            </Card>
          ))}
        </div>
      </div>

      {/* Apply Button */}
      <div className={styles.footer}>
        <Button
          data-testid="aiml-apply-button"
          appearance="primary"
          icon={<CheckmarkCircleRegular />}
          disabled={!selectedGpu && !selectedRefArch}
          onClick={handleApply}
        >
          Apply Configuration
        </Button>
      </div>
    </div>
  );
};

export default AiMlAcceleratorPanel;
