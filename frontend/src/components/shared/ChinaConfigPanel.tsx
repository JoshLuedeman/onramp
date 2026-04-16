import {
  Dropdown,
  Field,
  Option,
  Radio,
  RadioGroup,
  Text,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import type { OptionOnSelectData, SelectionEvents } from "@fluentui/react-components";
import {
  GlobeLocationRegular,
  ShieldCheckmarkRegular,
  InfoRegular,
} from "@fluentui/react-icons";
import { useCallback, useMemo } from "react";

// ── Types ───────────────────────────────────────────────────────────────────

export interface ChinaRegion {
  name: string;
  display_name: string;
  paired_region: string;
}

export interface ChinaConfig {
  icpLicenseStatus: "yes" | "no" | "in_progress";
  mlpsLevel: "level2" | "level3" | "level4";
  region: string;
  dataResidency: "mainland_only" | "include_hongkong";
  supportTier: "standard" | "professional" | "premier";
}

export interface ChinaConfigPanelProps {
  config: ChinaConfig;
  onConfigChange: (config: ChinaConfig) => void;
  disabled?: boolean;
}

// ── Region Data ─────────────────────────────────────────────────────────────

const CHINA_REGIONS: ChinaRegion[] = [
  { name: "chinanorth", display_name: "China North (Beijing)", paired_region: "chinaeast" },
  { name: "chinanorth2", display_name: "China North 2 (Beijing)", paired_region: "chinaeast2" },
  { name: "chinanorth3", display_name: "China North 3 (Hebei)", paired_region: "chinaeast3" },
  { name: "chinaeast", display_name: "China East (Shanghai)", paired_region: "chinanorth" },
  { name: "chinaeast2", display_name: "China East 2 (Shanghai)", paired_region: "chinanorth2" },
  { name: "chinaeast3", display_name: "China East 3 (Jiangsu)", paired_region: "chinanorth3" },
];

// ── Styles ──────────────────────────────────────────────────────────────────

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
    paddingBottom: tokens.spacingVerticalS,
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
  },
  pairedRegionInfo: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalXS,
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
    paddingLeft: tokens.spacingHorizontalS,
  },
  dataResidencyBadge: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalXS,
    backgroundColor: tokens.colorPaletteGreenBackground1,
    color: tokens.colorPaletteGreenForeground1,
    padding: `${tokens.spacingVerticalXS} ${tokens.spacingHorizontalS}`,
    borderRadius: tokens.borderRadiusMedium,
    fontSize: tokens.fontSizeBase200,
    fontWeight: tokens.fontWeightSemibold,
  },
});

// ── Component ───────────────────────────────────────────────────────────────

export default function ChinaConfigPanel({
  config,
  onConfigChange,
  disabled = false,
}: ChinaConfigPanelProps) {
  const styles = useStyles();

  const handleChange = useCallback(
    (field: keyof ChinaConfig, value: string) => {
      onConfigChange({ ...config, [field]: value });
    },
    [config, onConfigChange],
  );

  const selectedRegion = useMemo(
    () => CHINA_REGIONS.find((r) => r.name === config.region),
    [config.region],
  );

  const handleRegionSelect = useCallback(
    (_event: SelectionEvents, data: OptionOnSelectData) => {
      if (data.optionValue) {
        handleChange("region", data.optionValue);
      }
    },
    [handleChange],
  );

  return (
    <div className={styles.container} data-testid="china-config-panel">
      {/* Header */}
      <div className={styles.header}>
        <GlobeLocationRegular />
        <Text weight="semibold" size={400}>
          Azure China (21Vianet) Configuration
        </Text>
      </div>

      {/* Data Residency Indicator */}
      <div className={styles.dataResidencyBadge}>
        <ShieldCheckmarkRegular />
        <span>
          Data residency:{" "}
          {config.dataResidency === "mainland_only"
            ? "Mainland China only"
            : "Hong Kong included"}
        </span>
      </div>

      {/* ICP License Status */}
      <div className={styles.section}>
        <Field label="ICP License Status">
          <RadioGroup
            value={config.icpLicenseStatus}
            onChange={(_e, data) => handleChange("icpLicenseStatus", data.value)}
            disabled={disabled}
            aria-label="ICP license status"
          >
            <Radio value="yes" label="Yes — licensed" />
            <Radio value="no" label="No" />
            <Radio value="in_progress" label="In progress" />
          </RadioGroup>
        </Field>
      </div>

      {/* MLPS Level */}
      <div className={styles.section}>
        <Field label="MLPS Certification Level">
          <RadioGroup
            value={config.mlpsLevel}
            onChange={(_e, data) => handleChange("mlpsLevel", data.value)}
            disabled={disabled}
            aria-label="MLPS certification level"
          >
            <Radio value="level2" label="Level 2 — General systems" />
            <Radio value="level3" label="Level 3 — Important systems" />
            <Radio value="level4" label="Level 4 — Critical systems" />
          </RadioGroup>
        </Field>
      </div>

      {/* Region Dropdown */}
      <div className={styles.section}>
        <Field label="China Region">
          <Dropdown
            value={selectedRegion?.display_name ?? ""}
            selectedOptions={[config.region]}
            onOptionSelect={handleRegionSelect}
            disabled={disabled}
            aria-label="China region"
          >
            {CHINA_REGIONS.map((region) => (
              <Option key={region.name} value={region.name} text={region.display_name}>
                {region.display_name}
              </Option>
            ))}
          </Dropdown>
        </Field>
        {selectedRegion && (
          <div className={styles.pairedRegionInfo}>
            <InfoRegular />
            <span>
              Paired region: {CHINA_REGIONS.find((r) => r.name === selectedRegion.paired_region)?.display_name ?? selectedRegion.paired_region}
            </span>
          </div>
        )}
      </div>

      {/* Data Residency */}
      <div className={styles.section}>
        <Field label="Data Residency Requirement">
          <RadioGroup
            value={config.dataResidency}
            onChange={(_e, data) => handleChange("dataResidency", data.value)}
            disabled={disabled}
            aria-label="Data residency requirement"
          >
            <Radio value="mainland_only" label="Mainland China only" />
            <Radio value="include_hongkong" label="Hong Kong included" />
          </RadioGroup>
        </Field>
      </div>

      {/* Support Tier */}
      <div className={styles.section}>
        <Field label="21Vianet Support Tier">
          <RadioGroup
            value={config.supportTier}
            onChange={(_e, data) => handleChange("supportTier", data.value)}
            disabled={disabled}
            aria-label="21Vianet support tier"
          >
            <Radio value="standard" label="Standard" />
            <Radio value="professional" label="Professional" />
            <Radio value="premier" label="Premier" />
          </RadioGroup>
        </Field>
      </div>
    </div>
  );
}

export { CHINA_REGIONS };
