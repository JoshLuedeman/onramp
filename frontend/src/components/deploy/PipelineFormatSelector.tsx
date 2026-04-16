import { useState } from "react";
import {
  RadioGroup,
  Radio,
  Text,
  Input,
  Label,
  Card,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import type { RadioGroupOnChangeData } from "@fluentui/react-components";
import IaCFormatSelector from "../shared/IaCFormatSelector";
import type { IaCFormat } from "../shared/IaCFormatSelector";

export type PipelineFormat = "github_actions" | "azure_devops";

export interface PipelineConfig {
  pipelineFormat: PipelineFormat;
  iacFormat: IaCFormat;
  serviceConnection: string;
}

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalM,
  },
  sectionLabel: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase300,
  },
  optionDescription: {
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
    marginLeft: "28px",
  },
  subSection: {
    padding: tokens.spacingVerticalS,
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
  },
  inputGroup: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXS,
  },
});

export interface PipelineFormatSelectorProps {
  config: PipelineConfig;
  onConfigChange: (config: PipelineConfig) => void;
  disabled?: boolean;
}

export default function PipelineFormatSelector({
  config,
  onConfigChange,
  disabled = false,
}: PipelineFormatSelectorProps) {
  const styles = useStyles();
  const [showDescription, setShowDescription] = useState<PipelineFormat>(
    config.pipelineFormat,
  );

  const handlePipelineChange = (
    _event: React.FormEvent<HTMLDivElement>,
    data: RadioGroupOnChangeData,
  ) => {
    const format = data.value as PipelineFormat;
    setShowDescription(format);
    onConfigChange({ ...config, pipelineFormat: format });
  };

  const handleIaCFormatChange = (iacFormat: IaCFormat) => {
    onConfigChange({ ...config, iacFormat });
  };

  const handleServiceConnectionChange = (
    _event: React.ChangeEvent<HTMLInputElement>,
    data: { value: string },
  ) => {
    onConfigChange({ ...config, serviceConnection: data.value });
  };

  return (
    <div className={styles.container}>
      <Text className={styles.sectionLabel}>Pipeline Provider</Text>
      <RadioGroup
        value={config.pipelineFormat}
        onChange={handlePipelineChange}
        disabled={disabled}
        aria-label="CI/CD pipeline format"
      >
        <Radio value="github_actions" label="GitHub Actions" />
        <Radio value="azure_devops" label="Azure DevOps Pipelines" />
      </RadioGroup>
      {showDescription === "github_actions" && (
        <Text className={styles.optionDescription}>
          Generates workflow YAML files for GitHub Actions CI/CD
        </Text>
      )}
      {showDescription === "azure_devops" && (
        <Text className={styles.optionDescription}>
          Generates pipeline YAML files for Azure DevOps
        </Text>
      )}

      <Card className={styles.subSection}>
        <Text className={styles.sectionLabel}>Target IaC Format</Text>
        <IaCFormatSelector
          selectedFormat={config.iacFormat}
          onFormatChange={handleIaCFormatChange}
          disabled={disabled}
        />
      </Card>

      {config.pipelineFormat === "azure_devops" && (
        <div className={styles.inputGroup}>
          <Label htmlFor="service-connection-input">
            Service Connection Name
          </Label>
          <Input
            id="service-connection-input"
            placeholder="e.g., AzureServiceConnection"
            value={config.serviceConnection}
            onChange={handleServiceConnectionChange}
            disabled={disabled}
            aria-label="Azure DevOps service connection name"
          />
        </div>
      )}
    </div>
  );
}
