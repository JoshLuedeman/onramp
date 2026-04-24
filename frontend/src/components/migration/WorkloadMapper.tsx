import { useCallback, useEffect, useState } from "react";
import {
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
  WarningRegular,
} from "@fluentui/react-icons";
import type { WorkloadMappingRecord, WorkloadRecord } from "../../services/api";
import { api } from "../../services/api";
import WorkloadMapperSourcePane from "./WorkloadMapperSourcePane";
import WorkloadMapperTargetPane from "./WorkloadMapperTargetPane";

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
  warningsSection: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXS,
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
    [draggingId, subscriptions, workloads, overrides, mappings]
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
        <WorkloadMapperSourcePane
          workloads={workloads}
          groupedWorkloads={groupedWorkloads}
          mappingByWorkloadId={mappingByWorkloadId}
          draggingId={draggingId}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        />

        {/* Right — subscription targets */}
        <WorkloadMapperTargetPane
          subscriptions={subscriptions}
          workloadsBySubscription={workloadsBySubscription}
          mappings={mappings}
          dragOverSubId={dragOverSubId}
          onDragOver={setDragOverSubId}
          onDragLeave={() => setDragOverSubId(null)}
          onDrop={handleDrop}
        />
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
