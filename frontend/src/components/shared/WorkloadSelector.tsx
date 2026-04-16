import {
  Card,
  CardHeader,
  Text,
  Badge,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  BrainCircuitRegular,
  ServerRegular,
  DesktopRegular,
  BoardRegular,
} from "@fluentui/react-icons";
import type { ReactElement } from "react";

export interface WorkloadOption {
  workload_type: string;
  display_name: string;
  description: string;
  icon: ReactElement;
  tag_count: number;
}

const DEFAULT_WORKLOADS: WorkloadOption[] = [
  {
    workload_type: "ai_ml",
    display_name: "AI / Machine Learning",
    description: "GPU compute, model training, inference and MLOps",
    icon: <BrainCircuitRegular />,
    tag_count: 4,
  },
  {
    workload_type: "sap",
    display_name: "SAP",
    description: "SAP HANA, S/4HANA and certified VM families",
    icon: <ServerRegular />,
    tag_count: 3,
  },
  {
    workload_type: "avd",
    display_name: "Azure Virtual Desktop",
    description: "Desktop virtualization with session hosts",
    icon: <DesktopRegular />,
    tag_count: 3,
  },
  {
    workload_type: "iot",
    display_name: "IoT / Edge",
    description: "IoT Hub, Edge devices and telemetry ingestion",
    icon: <BoardRegular />,
    tag_count: 3,
  },
];

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexWrap: "wrap",
    gap: tokens.spacingHorizontalM,
  },
  card: {
    width: "220px",
    cursor: "pointer",
    transitionDuration: tokens.durationFast,
    transitionProperty: "border-color, box-shadow",
    ":hover": {
      boxShadow: tokens.shadow8,
    },
  },
  cardSelected: {
    width: "220px",
    cursor: "pointer",
    borderTopColor: tokens.colorBrandStroke1,
    borderRightColor: tokens.colorBrandStroke1,
    borderBottomColor: tokens.colorBrandStroke1,
    borderLeftColor: tokens.colorBrandStroke1,
    borderTopWidth: "2px",
    borderRightWidth: "2px",
    borderBottomWidth: "2px",
    borderLeftWidth: "2px",
    borderTopStyle: "solid",
    borderRightStyle: "solid",
    borderBottomStyle: "solid",
    borderLeftStyle: "solid",
    boxShadow: tokens.shadow8,
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
  },
  icon: {
    fontSize: tokens.fontSizeBase500,
    color: tokens.colorBrandForeground1,
  },
  description: {
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
  },
  badge: {
    marginTop: tokens.spacingVerticalXS,
  },
});

export interface WorkloadSelectorProps {
  selected: string | null;
  onSelect: (workloadType: string) => void;
  workloads?: WorkloadOption[];
  disabled?: boolean;
}

export default function WorkloadSelector({
  selected,
  onSelect,
  workloads = DEFAULT_WORKLOADS,
  disabled = false,
}: WorkloadSelectorProps) {
  const styles = useStyles();

  return (
    <div className={styles.container} role="radiogroup" aria-label="Workload type">
      {workloads.map((wl) => {
        const isSelected = selected === wl.workload_type;
        return (
          <Card
            key={wl.workload_type}
            className={isSelected ? styles.cardSelected : styles.card}
            onClick={() => !disabled && onSelect(wl.workload_type)}
            role="radio"
            aria-checked={isSelected}
            aria-label={wl.display_name}
          >
            <CardHeader
              header={
                <div className={styles.header}>
                  <span className={styles.icon}>{wl.icon}</span>
                  <Text weight="semibold">{wl.display_name}</Text>
                </div>
              }
              description={
                <Text className={styles.description}>{wl.description}</Text>
              }
            />
            <div className={styles.badge}>
              <Badge appearance="outline" color="informative">
                {wl.tag_count} questions
              </Badge>
            </div>
          </Card>
        );
      })}
    </div>
  );
}

export { DEFAULT_WORKLOADS };
