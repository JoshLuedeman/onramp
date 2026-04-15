import { useCallback, useEffect, useState } from "react";
import {
  Badge,
  Button,
  MessageBar,
  MessageBarBody,
  Spinner,
  Text,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  ArrowSyncRegular,
  CheckmarkCircleRegular,
  WarningRegular,
} from "@fluentui/react-icons";
import type { WorkloadMappingRecord, WorkloadRecord } from "../../services/api";
import { api } from "../../services/api";

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const useStyles = makeStyles({
  root: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalM,
    padding: tokens.spacingHorizontalM,
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    flexWrap: "wrap",
    gap: tokens.spacingHorizontalS,
  },
  title: {
    fontSize: tokens.fontSizeBase500,
    fontWeight: tokens.fontWeightSemibold,
  },
  panes: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: tokens.spacingHorizontalL,
  },
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
    padding: `${tokens.spacingVerticalXXS} ${tokens.spacingHorizontalXS}`,
    borderRadius: tokens.borderRadiusSmall,
    backgroundColor: tokens.colorNeutralBackground3,
  },
  warningsSection: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXS,
  },
  errorText: {
    color: tokens.colorPaletteRedForeground1,
  },
  emptyHint: {
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
    fontStyle: "italic",
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
  groupLabel: {
    fontSize: tokens.fontSizeBase200,
    fontWeight: tokens.fontWeightSemibold,
    color: tokens.colorNeutralForeground2,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    marginTop: tokens.spacingVerticalS,
  },
});

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SubscriptionDef {
  id: string;
  name: string;
  purpose: string;
}

interface WorkloadMapperProps {
  projectId: string;
  /** Optional architecture subscriptions — loaded externally or from state */
  subscriptions?: SubscriptionDef[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function confidenceLabel(score: number): string {
  if (score >= 0.8) return "High";
  if (score >= 0.5) return "Medium";
  return "Low";
}

function groupByType(workloads: WorkloadRecord[]): Record<string, WorkloadRecord[]> {
  const groups: Record<string, WorkloadRecord[]> = {};
  for (const wl of workloads) {
    const key = wl.type || "other";
    (groups[key] ??= []).push(wl);
  }
  return groups;
}

// ---------------------------------------------------------------------------
// WorkloadMapper
// ---------------------------------------------------------------------------

export default function WorkloadMapper({ projectId, subscriptions: propSubscriptions }: WorkloadMapperProps) {
  const styles = useStyles();

  const [workloads, setWorkloads] = useState<WorkloadRecord[]>([]);
  const [subscriptions, setSubscriptions] = useState<SubscriptionDef[]>(propSubscriptions ?? []);
  const [mappings, setMappings] = useState<WorkloadMappingRecord[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dragOverSubId, setDragOverSubId] = useState<string | null>(null);

  // Load workloads on mount
  useEffect(() => {
    api.workloads.list(projectId)
      .then((res) => setWorkloads(res.workloads))
      .catch(() => setWorkloads([]));
  }, [projectId]);

  // Load subscriptions from project architecture when not provided via props
  useEffect(() => {
    if (propSubscriptions && propSubscriptions.length > 0) {
      setSubscriptions(propSubscriptions);
      return;
    }
    api.architecture.getByProject(projectId)
      .then((res) => {
        const subs = res.architecture?.subscriptions;
        if (Array.isArray(subs) && subs.length > 0) {
          setSubscriptions(
            subs.map((s, i) => ({
              id: (s as { id?: string; name?: string }).id ?? (s as { name?: string }).name ?? `sub-${i}`,
              name: (s as { name?: string }).name ?? `sub-${i}`,
              purpose: (s as { purpose?: string }).purpose ?? "",
            }))
          );
        }
      })
      .catch(() => {/* silently skip if no architecture */});
  }, [projectId, propSubscriptions]);

  // ---------------------------------------------------------------------------
  // Generate Mapping
  // ---------------------------------------------------------------------------

  const handleGenerateMapping = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.workloads.generateMapping(projectId, "", true);
      setMappings(res.mappings);
      setWarnings(res.warnings);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate mapping");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  // ---------------------------------------------------------------------------
  // Drag-and-drop
  // ---------------------------------------------------------------------------

  const handleDragStart = useCallback((workloadId: string) => {
    setDraggingId(workloadId);
  }, []);

  const handleDragEnd = useCallback(() => {
    setDraggingId(null);
    setDragOverSubId(null);
  }, []);

  const handleDrop = useCallback(
    async (subscriptionId: string) => {
      if (!draggingId) return;
      setDragOverSubId(null);

      const sub = subscriptions.find((s) => s.id === subscriptionId);
      const subName = sub?.name ?? subscriptionId;

      // Capture previous state for revert on failure
      const prevOverrides = overrides;
      const prevMappings = mappings;

      // Optimistic update
      setOverrides((prev) => ({ ...prev, [draggingId]: subscriptionId }));

      // Update mapping in local state
      setMappings((prev) => {
        const existing = prev.find((m) => m.workload_id === draggingId);
        if (existing) {
          return prev.map((m) =>
            m.workload_id === draggingId
              ? { ...m, recommended_subscription_id: subscriptionId, recommended_subscription_name: subName }
              : m
          );
        }
        // No existing mapping — create one
        const wl = workloads.find((w) => w.id === draggingId);
        return [
          ...prev,
          {
            workload_id: draggingId,
            workload_name: wl?.name ?? draggingId,
            recommended_subscription_id: subscriptionId,
            recommended_subscription_name: subName,
            reasoning: "Manual assignment",
            confidence_score: 1.0,
            warnings: [],
          },
        ];
      });

      // Persist to backend
      try {
        await api.workloads.overrideMapping(draggingId, subscriptionId, "Manual drag-and-drop assignment");
      } catch {
        // Revert both overrides and mappings state on failure
        setOverrides(prevOverrides);
        setMappings(prevMappings);
        setError("Failed to save mapping override — please try again.");
      }
      setDraggingId(null);
    },
    [draggingId, subscriptions, workloads]
  );

  // ---------------------------------------------------------------------------
  // Derived state
  // ---------------------------------------------------------------------------

  const mappingByWorkloadId: Record<string, WorkloadMappingRecord> = Object.fromEntries(
    mappings.map((m) => [m.workload_id, m])
  );

  const workloadsBySubscription: Record<string, string[]> = {};
  for (const m of mappings) {
    const subId = overrides[m.workload_id] ?? m.recommended_subscription_id;
    (workloadsBySubscription[subId] ??= []).push(m.workload_id);
  }

  const groupedWorkloads = groupByType(workloads);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className={styles.root}>
      {/* Header */}
      <div className={styles.header}>
        <Text className={styles.title}>Workload–Subscription Mapping</Text>
        <Button
          appearance="primary"
          icon={loading ? <Spinner size="tiny" /> : <ArrowSyncRegular />}
          disabled={loading || workloads.length === 0}
          onClick={handleGenerateMapping}
        >
          {loading ? "Generating…" : "Generate Mapping"}
        </Button>
      </div>

      {error && (
        <MessageBar intent="error">
          <MessageBarBody>{error}</MessageBarBody>
        </MessageBar>
      )}

      {/* Split panes */}
      <div className={styles.panes}>
        {/* Left — workload list */}
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
                    onDragStart={() => handleDragStart(wl.id)}
                    onDragEnd={handleDragEnd}
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

        {/* Right — subscription targets */}
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
                  setDragOverSubId(sub.id);
                }}
                onDragLeave={() => setDragOverSubId(null)}
                onDrop={() => handleDrop(sub.id)}
                data-testid={`subscription-target-${sub.id}`}
              >
                <Text className={styles.subscriptionName}>{sub.name}</Text>
                <Text className={styles.subscriptionPurpose}>{sub.purpose}</Text>
                {assignedIds.length > 0 && (
                  <div className={styles.assignedList}>
                    {assignedIds.map((wlId) => {
                      const m = mappingByWorkloadId[wlId];
                      return (
                        <div key={wlId} className={styles.assignedChip}>
                          <CheckmarkCircleRegular fontSize="12px" />
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
      </div>

      {/* Validation warnings */}
      {warnings.length > 0 && (
        <div className={styles.warningsSection}>
          {warnings.map((w, i) => (
            <MessageBar key={i} intent="warning">
              <MessageBarBody>
                <WarningRegular /> {w}
              </MessageBarBody>
            </MessageBar>
          ))}
        </div>
      )}
    </div>
  );
}
