import { useCallback, useMemo } from "react";
import {
  Checkbox,
  Dropdown,
  Label,
  Option,
  RadioGroup,
  Radio,
  Text,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import type {
  CheckboxOnChangeData,
  OptionOnSelectData,
  RadioGroupOnChangeData,
  SelectionEvents,
} from "@fluentui/react-components";
import { ShieldKeyholeRegular } from "@fluentui/react-icons";

// ── Types ───────────────────────────────────────────────────────────────────

export type ImpactLevel = "IL2" | "IL4" | "IL5" | "IL6";
export type FedRAMPLevel = "high" | "moderate" | "low";

export interface GovernmentConfig {
  impactLevel: ImpactLevel;
  dodWorkload: boolean;
  fedrampLevel: FedRAMPLevel;
  itarRequired: boolean;
  region: string;
}

export interface GovernmentRegionOption {
  name: string;
  displayName: string;
  restricted: boolean;
}

export interface GovernmentConfigPanelProps {
  config: GovernmentConfig;
  onConfigChange: (config: GovernmentConfig) => void;
  regions?: GovernmentRegionOption[];
  disabled?: boolean;
}

// ── Styles ──────────────────────────────────────────────────────────────────

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalM,
    padding: tokens.spacingVerticalM,
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
  },
  headerIcon: {
    color: tokens.colorBrandForeground1,
    fontSize: tokens.fontSizeBase500,
  },
  section: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
  },
  description: {
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
  },
  regionGroup: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground2,
    paddingTop: tokens.spacingVerticalXS,
  },
});

// ── Default Regions (when none provided via props) ──────────────────────────

const DEFAULT_REGIONS: GovernmentRegionOption[] = [
  { name: "usgovvirginia", displayName: "US Gov Virginia", restricted: false },
  { name: "usgovtexas", displayName: "US Gov Texas", restricted: false },
  { name: "usgoviowa", displayName: "US Gov Iowa", restricted: false },
  { name: "usgovarizona", displayName: "US Gov Arizona", restricted: false },
  { name: "usdodcentral", displayName: "US DoD Central", restricted: true },
  { name: "usdodeast", displayName: "US DoD East", restricted: true },
];

// ── Component ───────────────────────────────────────────────────────────────

export default function GovernmentConfigPanel({
  config,
  onConfigChange,
  regions = DEFAULT_REGIONS,
  disabled = false,
}: GovernmentConfigPanelProps) {
  const styles = useStyles();

  const dodRegions = useMemo(
    () => regions.filter((r) => r.restricted),
    [regions],
  );

  const nonDodRegions = useMemo(
    () => regions.filter((r) => !r.restricted),
    [regions],
  );

  const handleImpactLevelChange = useCallback(
    (_event: React.FormEvent, data: RadioGroupOnChangeData) => {
      onConfigChange({
        ...config,
        impactLevel: data.value as ImpactLevel,
      });
    },
    [config, onConfigChange],
  );

  const handleFedRAMPChange = useCallback(
    (_event: React.FormEvent, data: RadioGroupOnChangeData) => {
      onConfigChange({
        ...config,
        fedrampLevel: data.value as FedRAMPLevel,
      });
    },
    [config, onConfigChange],
  );

  const handleDodChange = useCallback(
    (_event: React.ChangeEvent<HTMLInputElement>, data: CheckboxOnChangeData) => {
      onConfigChange({
        ...config,
        dodWorkload: data.checked === true,
      });
    },
    [config, onConfigChange],
  );

  const handleItarChange = useCallback(
    (_event: React.ChangeEvent<HTMLInputElement>, data: CheckboxOnChangeData) => {
      onConfigChange({
        ...config,
        itarRequired: data.checked === true,
      });
    },
    [config, onConfigChange],
  );

  const handleRegionSelect = useCallback(
    (_event: SelectionEvents, data: OptionOnSelectData) => {
      if (data.optionValue) {
        onConfigChange({
          ...config,
          region: data.optionValue,
        });
      }
    },
    [config, onConfigChange],
  );

  const selectedRegionLabel = useMemo(() => {
    const found = regions.find((r) => r.name === config.region);
    return found?.displayName ?? "";
  }, [config.region, regions]);

  return (
    <div className={styles.container} data-testid="government-config-panel">
      {/* Header */}
      <div className={styles.header}>
        <ShieldKeyholeRegular className={styles.headerIcon} />
        <Text weight="semibold" size={400}>
          Azure Government Configuration
        </Text>
      </div>

      <Text className={styles.description}>
        Configure settings specific to Azure Government cloud deployments,
        including Impact Level, FedRAMP authorization, and region selection.
      </Text>

      {/* Impact Level */}
      <div className={styles.section}>
        <Label htmlFor="impact-level">Impact Level (IL)</Label>
        <RadioGroup
          id="impact-level"
          value={config.impactLevel}
          onChange={handleImpactLevelChange}
          disabled={disabled}
          aria-label="Impact Level"
        >
          <Radio value="IL2" label="IL2 — Non-Controlled Unclassified Information" />
          <Radio value="IL4" label="IL4 — Controlled Unclassified Information" />
          <Radio value="IL5" label="IL5 — Higher Sensitivity CUI" />
          <Radio value="IL6" label="IL6 — Classified (SECRET)" />
        </RadioGroup>
      </div>

      {/* FedRAMP Level */}
      <div className={styles.section}>
        <Label htmlFor="fedramp-level">FedRAMP Authorization Level</Label>
        <RadioGroup
          id="fedramp-level"
          value={config.fedrampLevel}
          onChange={handleFedRAMPChange}
          disabled={disabled}
          aria-label="FedRAMP Level"
        >
          <Radio value="high" label="High" />
          <Radio value="moderate" label="Moderate" />
          <Radio value="low" label="Low" />
        </RadioGroup>
      </div>

      {/* DoD Workload */}
      <div className={styles.section}>
        <Checkbox
          checked={config.dodWorkload}
          onChange={handleDodChange}
          disabled={disabled}
          label="DoD Workload"
        />
      </div>

      {/* ITAR Compliance */}
      <div className={styles.section}>
        <Checkbox
          checked={config.itarRequired}
          onChange={handleItarChange}
          disabled={disabled}
          label="ITAR Compliance Required"
        />
      </div>

      {/* Region Selector */}
      <div className={styles.section}>
        <Label htmlFor="gov-region">Government Region</Label>
        <Dropdown
          id="gov-region"
          value={selectedRegionLabel}
          selectedOptions={[config.region]}
          onOptionSelect={handleRegionSelect}
          disabled={disabled}
          aria-label="Government Region"
        >
          {nonDodRegions.length > 0 && (
            <>
              <Text className={styles.regionGroup}>Non-DoD Regions</Text>
              {nonDodRegions.map((r) => (
                <Option key={r.name} value={r.name} text={r.displayName}>
                  {r.displayName}
                </Option>
              ))}
            </>
          )}
          {dodRegions.length > 0 && (
            <>
              <Text className={styles.regionGroup}>DoD Regions</Text>
              {dodRegions.map((r) => (
                <Option key={r.name} value={r.name} text={r.displayName}>
                  {r.displayName}
                </Option>
              ))}
            </>
          )}
        </Dropdown>
      </div>
    </div>
  );
}
