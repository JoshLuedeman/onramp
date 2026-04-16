import {
  Dropdown,
  Option,
  Text,
  Tooltip,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import type { OptionOnSelectData, SelectionEvents } from "@fluentui/react-components";
import {
  GlobeRegular,
  ShieldKeyholeRegular,
  GlobeLocationRegular,
} from "@fluentui/react-icons";
import type { ReactElement } from "react";

export type CloudEnvironmentName = "commercial" | "government" | "china";

export interface CloudEnvironmentOption {
  value: CloudEnvironmentName;
  label: string;
  description: string;
  icon: ReactElement;
  restrictions: string[];
}

const CLOUD_ENVIRONMENTS: CloudEnvironmentOption[] = [
  {
    value: "commercial",
    label: "Azure Commercial",
    description: "Global Azure public cloud for commercial workloads",
    icon: <GlobeRegular />,
    restrictions: [],
  },
  {
    value: "government",
    label: "Azure Government",
    description: "Dedicated cloud for US government agencies and their partners",
    icon: <ShieldKeyholeRegular />,
    restrictions: [
      "Requires US government entity or sponsored partner",
      "FedRAMP High / DoD IL4-IL5 compliant",
    ],
  },
  {
    value: "china",
    label: "Azure China (21Vianet)",
    description: "Azure operated by 21Vianet for workloads in mainland China",
    icon: <GlobeLocationRegular />,
    restrictions: [
      "Operated by 21Vianet; separate identity and billing",
      "Requires a China-specific Azure subscription",
    ],
  },
];

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
  },
  description: {
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
    paddingLeft: tokens.spacingHorizontalS,
  },
  restrictionText: {
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorPaletteYellowForeground2,
    paddingLeft: tokens.spacingHorizontalS,
  },
});

export interface CloudEnvironmentSelectorProps {
  selectedEnvironment: CloudEnvironmentName;
  onChange: (environment: CloudEnvironmentName) => void;
  disabled?: boolean;
}

export default function CloudEnvironmentSelector({
  selectedEnvironment,
  onChange,
  disabled = false,
}: CloudEnvironmentSelectorProps) {
  const styles = useStyles();

  const handleSelect = (
    _event: SelectionEvents,
    data: OptionOnSelectData,
  ) => {
    if (data.optionValue) {
      onChange(data.optionValue as CloudEnvironmentName);
    }
  };

  const selectedOption = CLOUD_ENVIRONMENTS.find(
    (env) => env.value === selectedEnvironment,
  );

  return (
    <div className={styles.container}>
      <Dropdown
        value={selectedOption?.label ?? ""}
        selectedOptions={[selectedEnvironment]}
        onOptionSelect={handleSelect}
        disabled={disabled}
        aria-label="Cloud environment"
      >
        {CLOUD_ENVIRONMENTS.map((env) => (
          <Option key={env.value} value={env.value} text={env.label}>
            {env.icon} {env.label}
          </Option>
        ))}
      </Dropdown>
      {selectedOption && (
        <Text className={styles.description}>
          {selectedOption.description}
        </Text>
      )}
      {selectedOption && selectedOption.restrictions.length > 0 && (
        <Tooltip
          content={selectedOption.restrictions.join(". ")}
          relationship="description"
        >
          <Text className={styles.restrictionText}>
            ⚠ Restrictions apply
          </Text>
        </Tooltip>
      )}
    </div>
  );
}

export { CLOUD_ENVIRONMENTS };
