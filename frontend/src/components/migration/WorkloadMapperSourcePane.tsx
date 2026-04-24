import {
  Badge,
  Text,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import { CheckmarkCircleRegular } from "@fluentui/react-icons";
import type { WorkloadMappingRecord, WorkloadRecord } from "../../services/api";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface WorkloadMapperSourcePaneProps {
  workloads: WorkloadRecord[];
  groupedWorkloads: Record<string, WorkloadRecord[]>;
  mappingByWorkloadId: Record<string, WorkloadMappingRecord>;
  draggingId: string | null;
  onDragStart: (workloadId: string) => void;
  onDragEnd: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function confidenceLabel(score: number): string {
  if (score >= 0.8) return "High";
  if (score >= 0.5) return "Medium";
  return "Low";
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const useStyles = makeStyles({
  pane: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
  },
  paneTitle: {
    fontSize: tokens.fontSizeBase400,
    fontWeight: tokens.fontWeightSemibold,
    paddingBottom: tokens.spacingVerticalXS,
    borderBottomWidth: "2px",
    borderBottomStyle: "solid",
    borderBottomColor: tokens.colorBrandBackground,
  },
  emptyHint: {
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
    fontStyle: "italic",
  },
  groupLabel: {
    fontSize: tokens.fontSizeBase200,
    fontWeight: tokens.fontWeightSemibold,
    color: tokens.colorNeutralForeground2,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    marginTop: tokens.spacingVerticalS,
  },
  workloadCard: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXS,
    padding: tokens.spacingVerticalS,
    paddingLeft: tokens.spacingHorizontalS,
    paddingRight: tokens.spacingHorizontalS,
    borderRadius: tokens.borderRadiusMedium,
    borderTopWidth: "1px",
    borderBottomWidth: "1px",
    borderLeftWidth: "1px",
    borderRightWidth: "1px",
    borderTopStyle: "solid",
    borderBottomStyle: "solid",
    borderLeftStyle: "solid",
    borderRightStyle: "solid",
    borderTopColor: tokens.colorNeutralStroke1,
    borderBottomColor: tokens.colorNeutralStroke1,
    borderLeftColor: tokens.colorNeutralStroke1,
    borderRightColor: tokens.colorNeutralStroke1,
    backgroundColor: tokens.colorNeutralBackground1,
  },
  workloadCardDragging: {
    opacity: "0.5",
    backgroundColor: tokens.colorBrandBackground2,
  },
  workloadName: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase300,
  },
  workloadMeta: {
    display: "flex",
    gap: tokens.spacingHorizontalXS,
    flexWrap: "wrap",
    alignItems: "center",
  },
  mappingRow: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalXS,
    marginTop: tokens.spacingVerticalXS,
  },
  mappingText: {
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
  },
  confidenceHigh: {
    color: tokens.colorPaletteGreenForeground1,
  },
  confidenceMed: {
    color: tokens.colorPaletteMarigoldForeground1,
  },
  confidenceLow: {
    color: tokens.colorPaletteRedForeground1,
  },
});

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function WorkloadMapperSourcePane({
  workloads,
  groupedWorkloads,
  mappingByWorkloadId,
  draggingId,
  onDragStart,
  onDragEnd,
}: WorkloadMapperSourcePaneProps) {
  const styles = useStyles();

  return (
    <div className={styles.pane}>
      <Text className={styles.paneTitle}>Workloads</Text>
      {workloads.length === 0 && (
        <Text className={styles.emptyHint}>No workloads found for this project.</Text>
      )}
      {Object.entries(groupedWorkloads).map(([type, wls]) => (
        <div key={type}>
          <Text className={styles.groupLabel}>{type}</Text>
          {wls.map((wl) => {
            const mapping = mappingByWorkloadId[wl.id];
            const isDragging = draggingId === wl.id;
            return (
              <div
                key={wl.id}
                className={`${styles.workloadCard}${isDragging ? ` ${styles.workloadCardDragging}` : ""}`}
                draggable
                onDragStart={() => onDragStart(wl.id)}
                onDragEnd={onDragEnd}
                data-testid={`workload-card-${wl.id}`}
              >
                <Text className={styles.workloadName}>{wl.name}</Text>
                <div className={styles.workloadMeta}>
                  <Badge appearance="outline" size="small">{wl.criticality}</Badge>
                  {wl.compliance_requirements.length > 0 && (
                    <Badge appearance="tint" color="warning" size="small">
                      {wl.compliance_requirements.join(", ")}
                    </Badge>
                  )}
                </div>
                {mapping && (
                  <div className={styles.mappingRow}>
                    <CheckmarkCircleRegular />
                    <Text className={styles.mappingText}>
                      {mapping.recommended_subscription_name}
                    </Text>
                    <Badge appearance="tint" color="success" size="small">
                      Suggested
                    </Badge>
                    <Text
                      className={
                        mapping.confidence_score >= 0.8
                          ? styles.confidenceHigh
                          : mapping.confidence_score >= 0.5
                          ? styles.confidenceMed
                          : styles.confidenceLow
                      }
                    >
                      {confidenceLabel(mapping.confidence_score)} (
                      {Math.round(mapping.confidence_score * 100)}%)
                    </Text>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
