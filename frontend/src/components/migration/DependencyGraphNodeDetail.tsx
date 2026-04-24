import {
  Badge,
  MessageBar,
  MessageBarBody,
  Text,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import type { MigrationOrderResponse, WorkloadSummary } from "../../services/api";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface DependencyGraphNodeDetailProps {
  selectedNode: WorkloadSummary | null;
  cycleNodes: Set<string>;
  /** Pre-computed comma-separated names of workloads this node depends on. */
  dependsOnNames: string;
  /** Pre-computed comma-separated names of workloads that require this node. */
  requiredByNames: string;
  /** Total number of dependency edges for the selected node. */
  dependencyCount: number;
  migrationOrder: MigrationOrderResponse | null;
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const useStyles = makeStyles({
  detailPanel: {
    padding: tokens.spacingVerticalM,
    backgroundColor: tokens.colorNeutralBackground1,
    borderTopWidth: "1px",
    borderRightWidth: "1px",
    borderBottomWidth: "1px",
    borderLeftWidth: "1px",
    borderTopStyle: "solid",
    borderRightStyle: "solid",
    borderBottomStyle: "solid",
    borderLeftStyle: "solid",
    borderTopColor: tokens.colorNeutralStroke1,
    borderRightColor: tokens.colorNeutralStroke1,
    borderBottomColor: tokens.colorNeutralStroke1,
    borderLeftColor: tokens.colorNeutralStroke1,
    borderRadius: tokens.borderRadiusMedium,
  },
  detailContent: {
    marginTop: tokens.spacingVerticalS,
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXS,
  },
  detailRow: {
    display: "flex",
    gap: tokens.spacingHorizontalXS,
    alignItems: "baseline",
  },
  detailLabel: {
    color: tokens.colorNeutralForeground3,
  },
  migrationOrderSection: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
  },
  mutedText: {
    color: tokens.colorNeutralForeground3,
  },
  migrationGroupsTitle: {
    marginTop: tokens.spacingVerticalS,
  },
  orderList: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXS,
  },
  orderItem: {
    display: "flex",
    gap: tokens.spacingHorizontalS,
    alignItems: "center",
    paddingTop: tokens.spacingVerticalXS,
    paddingRight: tokens.spacingHorizontalS,
    paddingBottom: tokens.spacingVerticalXS,
    paddingLeft: tokens.spacingHorizontalS,
    backgroundColor: tokens.colorNeutralBackground1,
    borderRadius: tokens.borderRadiusMedium,
    borderTopWidth: "1px",
    borderRightWidth: "1px",
    borderBottomWidth: "1px",
    borderLeftWidth: "1px",
    borderTopStyle: "solid",
    borderRightStyle: "solid",
    borderBottomStyle: "solid",
    borderLeftStyle: "solid",
    borderTopColor: tokens.colorNeutralStroke1,
    borderRightColor: tokens.colorNeutralStroke1,
    borderBottomColor: tokens.colorNeutralStroke1,
    borderLeftColor: tokens.colorNeutralStroke1,
  },
});

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DependencyGraphNodeDetail({
  selectedNode,
  cycleNodes,
  dependsOnNames,
  requiredByNames,
  dependencyCount,
  migrationOrder,
}: DependencyGraphNodeDetailProps) {
  const styles = useStyles();

  return (
    <>
      {/* Node detail panel */}
      {selectedNode && (
        <div
          className={styles.detailPanel}
          aria-label={`Details for ${selectedNode.name}`}
        >
        <Text weight="semibold" size={400}>
          {selectedNode.name}
        </Text>
        <div className={styles.detailContent}>
          <div className={styles.detailRow}>
            <Text size={200} className={styles.detailLabel}>Criticality:</Text>
            <Badge
              appearance="tint"
              color={
                selectedNode.criticality === "mission-critical"
                  ? "danger"
                  : selectedNode.criticality === "business-critical"
                    ? "warning"
                    : "informative"
              }
              size="small"
            >
              {selectedNode.criticality}
            </Badge>
          </div>
          <div className={styles.detailRow}>
            <Text size={200} className={styles.detailLabel}>Migration strategy:</Text>
            <Text size={200}>{selectedNode.migration_strategy}</Text>
          </div>
          <div className={styles.detailRow}>
            <Text size={200} className={styles.detailLabel}>In cycle:</Text>
            <Text size={200}>{cycleNodes.has(selectedNode.id) ? "⚠ Yes" : "No"}</Text>
          </div>
          <div className={styles.detailRow}>
            <Text size={200} className={styles.detailLabel}>Dependencies:</Text>
            <Text size={200}>{dependencyCount}</Text>
          </div>
          <div className={styles.detailRow}>
            <Text size={200} className={styles.detailLabel}>Depends on:</Text>
            <Text size={200}>{dependsOnNames || "—"}</Text>
          </div>
          <div className={styles.detailRow}>
            <Text size={200} className={styles.detailLabel}>Required by:</Text>
            <Text size={200}>{requiredByNames || "—"}</Text>
          </div>
        </div>
      </div>
      )}

      {/* Migration order */}
      {migrationOrder && (
        <div className={styles.migrationOrderSection}>
          <Text weight="semibold" size={400}>
            Suggested Migration Order
          </Text>
          {migrationOrder.has_circular && (
            <MessageBar intent="warning">
              <MessageBarBody>
                Circular dependencies detected — order may be incomplete.
              </MessageBarBody>
            </MessageBar>
          )}
          {migrationOrder.order.length === 0 && (
            <Text className={styles.mutedText}>
              Cannot determine order due to circular dependencies.
            </Text>
          )}
          <div className={styles.orderList}>
            {migrationOrder.order.map((id, idx) => (
              <div key={id} className={styles.orderItem}>
                <Badge appearance="filled" size="small" color="brand">
                  {idx + 1}
                </Badge>
                <Text>{migrationOrder.workload_names[id] ?? id}</Text>
                {cycleNodes.has(id) && (
                  <Badge appearance="tint" color="danger" size="small">
                    cycle
                  </Badge>
                )}
              </div>
            ))}
          </div>
          {migrationOrder.migration_groups.length > 0 && (
            <>
              <Text weight="semibold" size={300} className={styles.migrationGroupsTitle}>
                Migration Groups
              </Text>
              {migrationOrder.migration_groups.map((group, idx) => (
                <div key={idx} className={styles.orderItem}>
                  <Badge appearance="tint" size="small">Group {idx + 1}</Badge>
                  <Text>
                    {group
                      .map((id) => migrationOrder.workload_names[id] ?? id)
                      .join(", ")}
                  </Text>
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </>
  );
}
