import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Text,
  makeStyles,
  tokens,
  Divider,
} from "@fluentui/react-components";
import {
  ChevronDownRegular,
  ChevronUpRegular,
  AddRegular,
  ErrorCircleRegular,
  WarningRegular,
  InfoRegular,
  CheckmarkCircleRegular,
} from "@fluentui/react-icons";
import type { GapFinding } from "../../services/api";

const useStyles = makeStyles({
  card: {
    padding: "16px",
    marginBottom: "8px",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "12px",
    cursor: "pointer",
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    flex: 1,
  },
  title: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase400,
  },
  category: {
    color: tokens.colorNeutralForeground3,
  },
  body: {
    marginTop: "12px",
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  },
  section: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
  },
  label: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
    textTransform: "uppercase",
  },
  cafRef: {
    fontFamily: "monospace",
    fontSize: tokens.fontSizeBase300,
    color: tokens.colorBrandForeground1,
  },
  remediationItem: {
    paddingLeft: "16px",
    fontSize: tokens.fontSizeBase300,
    color: tokens.colorNeutralForeground2,
  },
  actions: {
    display: "flex",
    gap: "8px",
    marginTop: "8px",
  },
});

type Severity = GapFinding["severity"];

function severityBadge(severity: Severity) {
  switch (severity) {
    case "critical":
      return (
        <Badge color="danger" appearance="filled" icon={<ErrorCircleRegular />}>
          Critical
        </Badge>
      );
    case "high":
      return (
        <Badge color="warning" appearance="filled" icon={<WarningRegular />}>
          High
        </Badge>
      );
    case "medium":
      return (
        <Badge color="informative" appearance="filled" icon={<InfoRegular />}>
          Medium
        </Badge>
      );
    case "low":
    default:
      return (
        <Badge color="subtle" appearance="filled" icon={<CheckmarkCircleRegular />}>
          Low
        </Badge>
      );
  }
}

interface GapFindingCardProps {
  finding: GapFinding;
  onAddToArchitecture?: (finding: GapFinding) => void;
}

export default function GapFindingCard({ finding, onAddToArchitecture }: GapFindingCardProps) {
  const styles = useStyles();
  const [expanded, setExpanded] = useState(false);

  return (
    <Card className={styles.card}>
      <div
        className={styles.header}
        onClick={() => setExpanded((e) => !e)}
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            setExpanded((v) => !v);
          }
          if (e.key === " ") {
            e.preventDefault();
            setExpanded((v) => !v);
          }
        }}
      >
        <div className={styles.headerLeft}>
          {severityBadge(finding.severity)}
          <Text className={styles.title}>{finding.title}</Text>
          <Text size={200} className={styles.category}>
            {finding.category}
          </Text>
        </div>
        {expanded ? <ChevronUpRegular /> : <ChevronDownRegular />}
      </div>

      {expanded && (
        <>
          <Divider style={{ margin: "12px 0" }} />
          <div className={styles.body}>
            <div className={styles.section}>
              <Text className={styles.label}>Description</Text>
              <Text size={300}>{finding.description}</Text>
            </div>

            {finding.caf_reference && (
              <div className={styles.section}>
                <Text className={styles.label}>CAF Reference</Text>
                <Text className={styles.cafRef}>{finding.caf_reference}</Text>
              </div>
            )}

            <div className={styles.section}>
              <Text className={styles.label}>Remediation</Text>
              <Text className={styles.remediationItem}>{finding.remediation}</Text>
            </div>

            <div className={styles.actions}>
              <Button
                appearance="secondary"
                icon={<AddRegular />}
                onClick={() => onAddToArchitecture?.(finding)}
              >
                Add to Architecture
              </Button>
            </div>
          </div>
        </>
      )}
    </Card>
  );
}
