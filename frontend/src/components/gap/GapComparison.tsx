import {
  Card,
  Text,
  Badge,
  makeStyles,
  tokens,
  Divider,
} from "@fluentui/react-components";
import {
  CheckmarkCircleRegular,
  WarningRegular,
  ErrorCircleRegular,
} from "@fluentui/react-icons";
import type { GapAnalysisResponse, BrownfieldContextResponse } from "../../services/api";

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  title: {
    fontSize: tokens.fontSizeBase500,
    fontWeight: tokens.fontWeightSemibold,
  },
  columns: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "16px",
  },
  column: {
    padding: "16px",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  columnTitle: {
    fontSize: tokens.fontSizeBase400,
    fontWeight: tokens.fontWeightSemibold,
    marginBottom: "4px",
  },
  areaRow: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
    padding: "8px",
    borderRadius: tokens.borderRadiusMedium,
  },
  areaRowGood: {
    backgroundColor: tokens.colorPaletteGreenBackground1,
  },
  areaRowWarn: {
    backgroundColor: tokens.colorPaletteMarigoldBackground1,
  },
  areaRowBad: {
    backgroundColor: tokens.colorPaletteRedBackground1,
  },
  areaHeader: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  areaName: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase300,
  },
  areaDetail: {
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground2,
  },
  discoveredSection: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  discoveredItem: {
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground2,
  },
  confidenceBadge: {
    marginLeft: tokens.spacingHorizontalXS,
    fontSize: tokens.fontSizeBase100,
  },
  mutedText: {
    color: tokens.colorNeutralForeground3,
  },
  divider: {
    margin: `${tokens.spacingVerticalS} 0`,
  },
});

interface AreaComplianceStatus {
  area: string;
  severity: "good" | "warning" | "critical";
  findingCount: number;
  remediation: string;
}

function complianceIcon(severity: AreaComplianceStatus["severity"]) {
  switch (severity) {
    case "good":
      return <CheckmarkCircleRegular color={tokens.colorPaletteGreenForeground1} />;
    case "warning":
      return <WarningRegular color={tokens.colorPaletteMarigoldForeground2} />;
    case "critical":
      return <ErrorCircleRegular color={tokens.colorPaletteRedForeground1} />;
  }
}

function complianceBadgeColor(
  severity: AreaComplianceStatus["severity"]
): "success" | "warning" | "danger" {
  switch (severity) {
    case "good":
      return "success";
    case "warning":
      return "warning";
    case "critical":
      return "danger";
  }
}

interface GapComparisonProps {
  gapResult: GapAnalysisResponse;
  brownfieldContext: BrownfieldContextResponse;
}

export default function GapComparison({ gapResult, brownfieldContext }: GapComparisonProps) {
  const styles = useStyles();

  // Build area-level compliance status from findings
  const areaMap = new Map<string, AreaComplianceStatus>();

  for (const area of gapResult.areas_checked) {
    areaMap.set(area, { area, severity: "good", findingCount: 0, remediation: "No issues found." });
  }

  for (const finding of gapResult.findings) {
    const existing = areaMap.get(finding.category);
    const count = (existing?.findingCount ?? 0) + 1;
    const severity: AreaComplianceStatus["severity"] =
      finding.severity === "critical" || finding.severity === "high" ? "critical" : "warning";
    const prevSeverity = existing?.severity ?? "good";
    const worstSeverity: AreaComplianceStatus["severity"] =
      prevSeverity === "critical" || severity === "critical"
        ? "critical"
        : prevSeverity === "warning" || severity === "warning"
        ? "warning"
        : "good";

    areaMap.set(finding.category, {
      area: finding.category,
      severity: worstSeverity,
      findingCount: count,
      remediation: finding.remediation,
    });
  }

  const areas = Array.from(areaMap.values());
  const discoveredEntries = Object.entries(brownfieldContext.discovered_answers);

  return (
    <div className={styles.container}>
      <Text className={styles.title}>Current vs Recommended Architecture</Text>

      <div className={styles.columns}>
        {/* Current State */}
        <Card className={styles.column}>
          <Text className={styles.columnTitle}>Current State</Text>
          <Divider className={styles.divider} />
          {discoveredEntries.length === 0 ? (
            <Text size={200} className={styles.mutedText}>
              No discovered context available.
            </Text>
          ) : (
            <div className={styles.discoveredSection}>
              {discoveredEntries.slice(0, 10).map(([key, answer]) => (
                <div key={key} className={styles.discoveredItem}>
                  <Text size={200} weight="semibold">
                    {key.replace(/_/g, " ")}:{" "}
                  </Text>
                  <Text size={200}>
                    {Array.isArray(answer.value)
                      ? answer.value.join(", ")
                      : String(answer.value)}
                  </Text>
                  <Badge
                    className={styles.confidenceBadge}
                    color={
                      answer.confidence === "high"
                        ? "success"
                        : answer.confidence === "medium"
                        ? "warning"
                        : "subtle"
                    }
                    size="small"
                    appearance="tint"
                  >
                    {answer.confidence}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Recommended State */}
        <Card className={styles.column}>
          <Text className={styles.columnTitle}>Recommended State</Text>
          <Divider className={styles.divider} />
          {areas.length === 0 ? (
            <Text size={200} className={styles.mutedText}>
              No areas analyzed.
            </Text>
          ) : (
            areas.map((item) => (
              <div
                key={item.area}
                className={`${styles.areaRow} ${
                  item.severity === "good"
                    ? styles.areaRowGood
                    : item.severity === "warning"
                    ? styles.areaRowWarn
                    : styles.areaRowBad
                }`}
              >
                <div className={styles.areaHeader}>
                  {complianceIcon(item.severity)}
                  <Text className={styles.areaName}>{item.area}</Text>
                  <Badge
                    color={complianceBadgeColor(item.severity)}
                    size="small"
                    appearance="tint"
                  >
                    {item.findingCount > 0
                      ? `${item.findingCount} finding${item.findingCount > 1 ? "s" : ""}`
                      : "Compliant"}
                  </Badge>
                </div>
                {item.findingCount > 0 && (
                  <Text className={styles.areaDetail}>{item.remediation}</Text>
                )}
              </div>
            ))
          )}
        </Card>
      </div>
    </div>
  );
}
