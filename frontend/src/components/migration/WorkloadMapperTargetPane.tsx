import {
  Text,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import type { WorkloadMappingRecord } from "../../services/api";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface SubscriptionDef {
  id: string;
  name: string;
  purpose: string;
}

interface WorkloadMapperTargetPaneProps {
  subscriptions: SubscriptionDef[];
  workloadsBySubscription: Record<string, string[]>;
  mappings: WorkloadMappingRecord[];
  dragOverSubId: string | null;
  onDragOver: (subscriptionId: string) => void;
  onDragLeave: () => void;
  onDrop: (subscriptionId: string) => void;
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
  subscriptionCard: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXS,
    padding: tokens.spacingVerticalS,
    paddingLeft: tokens.spacingHorizontalS,
    paddingRight: tokens.spacingHorizontalS,
    borderRadius: tokens.borderRadiusMedium,
    borderTopWidth: "2px",
    borderBottomWidth: "2px",
    borderLeftWidth: "2px",
    borderRightWidth: "2px",
    borderTopStyle: "dashed",
    borderBottomStyle: "dashed",
    borderLeftStyle: "dashed",
    borderRightStyle: "dashed",
    borderTopColor: tokens.colorNeutralStroke2,
    borderBottomColor: tokens.colorNeutralStroke2,
    borderLeftColor: tokens.colorNeutralStroke2,
    borderRightColor: tokens.colorNeutralStroke2,
    backgroundColor: tokens.colorNeutralBackground2,
    minHeight: "64px",
  },
  subscriptionCardOver: {
    borderTopColor: tokens.colorBrandBackground,
    borderBottomColor: tokens.colorBrandBackground,
    borderLeftColor: tokens.colorBrandBackground,
    borderRightColor: tokens.colorBrandBackground,
    backgroundColor: tokens.colorBrandBackground2,
  },
  subscriptionName: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase300,
  },
  subscriptionPurpose: {
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
  },
  assignedList: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXS,
    marginTop: tokens.spacingVerticalXS,
  },
  assignedChip: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalXS,
    fontSize: tokens.fontSizeBase200,
    paddingTop: tokens.spacingVerticalXXS,
    paddingRight: tokens.spacingHorizontalXS,
    paddingBottom: tokens.spacingVerticalXXS,
    paddingLeft: tokens.spacingHorizontalXS,
    borderRadius: tokens.borderRadiusSmall,
    backgroundColor: tokens.colorNeutralBackground3,
  },
});

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function WorkloadMapperTargetPane({
  subscriptions,
  workloadsBySubscription,
  mappings,
  dragOverSubId,
  onDragOver,
  onDragLeave,
  onDrop,
}: WorkloadMapperTargetPaneProps) {
  const styles = useStyles();

  return (
    <div className={styles.pane}>
      <Text className={styles.paneTitle}>Target Subscriptions</Text>
      {subscriptions.length === 0 && (
        <Text className={styles.emptyHint}>
          No subscriptions available. Generate an architecture first.
        </Text>
      )}
      {subscriptions.map((sub) => {
        const assignedIds = workloadsBySubscription[sub.id] ?? [];
        const isOver = dragOverSubId === sub.id;
        return (
          <div
            key={sub.id}
            className={`${styles.subscriptionCard}${isOver ? ` ${styles.subscriptionCardOver}` : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              onDragOver(sub.id);
            }}
            onDragLeave={() => onDragLeave()}
            onDrop={() => onDrop(sub.id)}
            data-testid={`subscription-target-${sub.id}`}
          >
            <Text className={styles.subscriptionName}>{sub.name}</Text>
            <Text className={styles.subscriptionPurpose}>{sub.purpose}</Text>
            {assignedIds.length > 0 && (
              <div className={styles.assignedList}>
                {assignedIds.map((wlId) => {
                  const m = mappings.find((mm) => mm.workload_id === wlId);
                  return (
                    <div key={wlId} className={styles.assignedChip}>
                      <Text>{m?.workload_name ?? wlId}</Text>
                    </div>
                  );
                })}
              </div>
            )}
            {assignedIds.length === 0 && (
              <Text className={styles.emptyHint}>Drop workloads here</Text>
            )}
          </div>
        );
      })}
    </div>
  );
}
