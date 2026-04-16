import { useState } from "react";
import {
  Card,
  CardHeader,
  Text,
  Badge,
  Button,
  Dropdown,
  Option,
  Switch,
  Spinner,
  MessageBar,
  MessageBarBody,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  ShieldLockRegular,
  ServerRegular,
  CheckmarkCircleRegular,
  InfoRegular,
} from "@fluentui/react-icons";
import type {
  ConfidentialOption,
  ConfidentialVmSku,
  ConfidentialRegion,
} from "../../services/api";

export interface ConfidentialComputingPanelProps {
  options: ConfidentialOption[];
  vmSkus: ConfidentialVmSku[];
  regions: ConfidentialRegion[];
  loading?: boolean;
  error?: string | null;
  onOptionSelect?: (optionId: string) => void;
  onSkuSelect?: (skuName: string) => void;
  onRegionSelect?: (regionName: string) => void;
  onAttestationToggle?: (enabled: boolean) => void;
  onApply?: (config: ConfidentialConfig) => void;
}

export interface ConfidentialConfig {
  selectedOption: string;
  selectedSku: string;
  selectedRegion: string;
  attestationEnabled: boolean;
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
  optionCard: {
    cursor: "pointer",
    padding: tokens.spacingVerticalS,
    borderRadius: tokens.borderRadiusMedium,
    "&:hover": {
      backgroundColor: tokens.colorNeutralBackground1Hover,
    },
  },
  optionCardSelected: {
    cursor: "pointer",
    padding: tokens.spacingVerticalS,
    borderRadius: tokens.borderRadiusMedium,
    backgroundColor: tokens.colorBrandBackground2,
    borderTopColor: tokens.colorBrandStroke1,
    borderRightColor: tokens.colorBrandStroke1,
    borderBottomColor: tokens.colorBrandStroke1,
    borderLeftColor: tokens.colorBrandStroke1,
  },
  optionsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
    gap: tokens.spacingVerticalS,
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
  useCaseList: {
    margin: 0,
    paddingLeft: tokens.spacingHorizontalL,
  },
  configRow: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalM,
  },
  description: {
    color: tokens.colorNeutralForeground2,
    fontSize: tokens.fontSizeBase200,
  },
  badge: {
    marginLeft: tokens.spacingHorizontalXS,
  },
});

const ConfidentialComputingPanel: React.FC<ConfidentialComputingPanelProps> = ({
  options,
  vmSkus,
  regions,
  loading = false,
  error = null,
  onOptionSelect,
  onSkuSelect,
  onRegionSelect,
  onAttestationToggle,
  onApply,
}) => {
  const styles = useStyles();
  const [selectedOption, setSelectedOption] = useState<string>("");
  const [selectedSku, setSelectedSku] = useState<string>("");
  const [selectedRegion, setSelectedRegion] = useState<string>("");
  const [attestationEnabled, setAttestationEnabled] = useState(true);

  const selectedOptionData = options.find((o) => o.id === selectedOption);

  // Filter regions to only those supporting the selected CC option
  const filteredRegions = selectedOption
    ? regions.filter((r) => r.services.includes(selectedOption))
    : regions;

  // Filter VM SKUs based on selected option's TEE types
  const filteredSkus = selectedOptionData
    ? vmSkus.filter((s) => selectedOptionData.tee_types.includes(s.tee_type))
    : vmSkus;

  const handleOptionSelect = (optionId: string) => {
    setSelectedOption(optionId);
    setSelectedSku("");
    setSelectedRegion("");
    onOptionSelect?.(optionId);
  };

  const handleSkuSelect = (skuName: string) => {
    setSelectedSku(skuName);
    onSkuSelect?.(skuName);
  };

  const handleRegionSelect = (regionName: string) => {
    setSelectedRegion(regionName);
    onRegionSelect?.(regionName);
  };

  const handleAttestationToggle = (checked: boolean) => {
    setAttestationEnabled(checked);
    onAttestationToggle?.(checked);
  };

  const handleApply = () => {
    onApply?.({
      selectedOption,
      selectedSku,
      selectedRegion,
      attestationEnabled,
    });
  };

  if (loading) {
    return (
      <div data-testid="cc-loading" className={styles.container}>
        <Spinner label="Loading confidential computing options..." />
      </div>
    );
  }

  if (error) {
    return (
      <div data-testid="cc-error" className={styles.container}>
        <MessageBar intent="error">
          <MessageBarBody>{error}</MessageBarBody>
        </MessageBar>
      </div>
    );
  }

  return (
    <div data-testid="cc-panel" className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <ShieldLockRegular fontSize={24} />
        <Text size={500} weight="semibold">
          Confidential Computing
        </Text>
      </div>

      <Text className={styles.description}>
        Enable hardware-based encryption using Trusted Execution Environments
        (TEEs) to protect data in use. Select a confidential computing option
        below to configure your deployment.
      </Text>

      {/* CC Option Selector */}
      <div className={styles.section}>
        <Text className={styles.sectionTitle}>
          Select Confidential Computing Option
        </Text>
        <div className={styles.optionsGrid}>
          {options.map((option) => (
            <Card
              key={option.id}
              data-testid={`cc-option-${option.id}`}
              className={
                selectedOption === option.id
                  ? styles.optionCardSelected
                  : styles.optionCard
              }
              onClick={() => handleOptionSelect(option.id)}
            >
              <CardHeader
                header={
                  <Text weight="semibold">
                    {option.name}
                    {option.tee_types.map((tee) => (
                      <Badge
                        key={tee}
                        appearance="outline"
                        size="small"
                        className={styles.badge}
                      >
                        {tee}
                      </Badge>
                    ))}
                  </Text>
                }
                description={
                  <Text className={styles.description}>
                    {option.description}
                  </Text>
                }
              />
            </Card>
          ))}
        </div>
      </div>

      {/* VM SKU Picker */}
      {selectedOptionData && selectedOptionData.vm_series.length > 0 && (
        <div className={styles.section}>
          <Text className={styles.sectionTitle}>
            <ServerRegular /> VM SKU
          </Text>
          <Dropdown
            placeholder="Select a VM SKU"
            data-testid="cc-sku-dropdown"
            value={selectedSku}
            onOptionSelect={(_e, data) =>
              handleSkuSelect(data.optionValue as string)
            }
          >
            {filteredSkus.map((sku) => (
              <Option key={sku.name} value={sku.name}>
                {sku.name} — {sku.vcpus} vCPUs, {sku.memory_gb} GiB RAM ({sku.tee_type})
              </Option>
            ))}
          </Dropdown>
        </div>
      )}

      {/* Region Filter */}
      <div className={styles.section}>
        <Text className={styles.sectionTitle}>Region</Text>
        <Dropdown
          placeholder="Select a region"
          data-testid="cc-region-dropdown"
          value={selectedRegion}
          onOptionSelect={(_e, data) =>
            handleRegionSelect(data.optionValue as string)
          }
        >
          {filteredRegions.map((region) => (
            <Option key={region.name} value={region.name}>
              {region.display_name} ({region.tee_types.join(", ")})
            </Option>
          ))}
        </Dropdown>
      </div>

      {/* Attestation Toggle */}
      <div className={styles.section}>
        <div className={styles.configRow}>
          <Switch
            data-testid="cc-attestation-toggle"
            label="Enable Azure Attestation"
            checked={attestationEnabled}
            onChange={(_e, data) => handleAttestationToggle(data.checked)}
          />
          <InfoRegular />
        </div>
        <Text className={styles.description}>
          Azure Attestation verifies the integrity of TEE environments before
          granting access to secrets and encryption keys.
        </Text>
      </div>

      {/* Selected Option Details */}
      {selectedOptionData && (
        <div className={styles.section}>
          <Text className={styles.sectionTitle}>
            <CheckmarkCircleRegular /> Use Cases
          </Text>
          <ul className={styles.useCaseList}>
            {selectedOptionData.use_cases.map((uc, idx) => (
              <li key={idx}>
                <Text size={200}>{uc}</Text>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Apply Button */}
      <Button
        appearance="primary"
        data-testid="cc-apply-button"
        disabled={!selectedOption}
        onClick={handleApply}
      >
        Apply Confidential Computing
      </Button>
    </div>
  );
};

export default ConfidentialComputingPanel;
