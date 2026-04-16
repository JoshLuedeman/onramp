import {
  TabList,
  Tab,
  Text,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import type { ReactElement } from "react";
import {
  CodeRegular,
  DocumentRegular,
  BranchRegular,
} from "@fluentui/react-icons";
import type { SelectTabData, SelectTabEvent } from "@fluentui/react-components";

export type IaCFormat = "bicep" | "terraform" | "arm" | "pulumi_ts" | "pulumi_python";

export interface IaCFormatOption {
  value: IaCFormat;
  label: string;
  description: string;
  icon: ReactElement;
}

const IAC_FORMATS: IaCFormatOption[] = [
  {
    value: "bicep",
    label: "Bicep",
    description: "Azure-native declarative IaC",
    icon: <CodeRegular />,
  },
  {
    value: "terraform",
    label: "Terraform",
    description: "Multi-cloud HCL configuration",
    icon: <DocumentRegular />,
  },
  {
    value: "arm",
    label: "ARM",
    description: "Azure Resource Manager JSON templates",
    icon: <BranchRegular />,
  },
  {
    value: "pulumi_ts",
    label: "Pulumi (TypeScript)",
    description: "IaC with TypeScript programming",
    icon: <CodeRegular />,
  },
  {
    value: "pulumi_python",
    label: "Pulumi (Python)",
    description: "IaC with Python programming",
    icon: <CodeRegular />,
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
});

export interface IaCFormatSelectorProps {
  selectedFormat: IaCFormat;
  onFormatChange: (format: IaCFormat) => void;
  disabled?: boolean;
}

export default function IaCFormatSelector({
  selectedFormat,
  onFormatChange,
  disabled = false,
}: IaCFormatSelectorProps) {
  const styles = useStyles();

  const handleTabSelect = (_event: SelectTabEvent, data: SelectTabData) => {
    onFormatChange(data.value as IaCFormat);
  };

  const selectedOption = IAC_FORMATS.find((f) => f.value === selectedFormat);

  return (
    <div className={styles.container}>
      <TabList
        selectedValue={selectedFormat}
        onTabSelect={handleTabSelect}
        size="small"
        disabled={disabled}
        aria-label="Infrastructure as Code format"
      >
        {IAC_FORMATS.map((format) => (
          <Tab key={format.value} value={format.value} icon={format.icon}>
            {format.label}
          </Tab>
        ))}
      </TabList>
      {selectedOption && (
        <Text className={styles.description}>
          {selectedOption.description}
        </Text>
      )}
    </div>
  );
}

export { IAC_FORMATS };
