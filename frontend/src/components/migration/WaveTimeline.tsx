import { useState, useCallback } from "react";
import {
  makeStyles,
  tokens,
  Card,
  CardHeader,
  Badge,
  Button,
  Text,
  Body1,
  Caption1,
  MessageBar,
  MessageBarBody,
  Tooltip,
} from "@fluentui/react-components";
import {
  ArrowUpRegular,
  ArrowDownRegular,
  WarningRegular,
} from "@fluentui/react-icons";
import type { WaveResponse, WaveWorkloadItem, ValidationWarning } from "../../services/api";

type BadgeColor = "informative" | "warning" | "severe" | "success" | "danger";

function criticalityColor(criticality: string): BadgeColor {
  switch (criticality) {
    case "mission-critical":
      return "danger";
    case "business-critical":
      return "severe";
    case "dev-test":
      return "informative";
    default:
      return "warning";
  }
}

function statusColor(status: string): BadgeColor {
  switch (status) {
    case "completed":
      return "success";
    case "in_progress":
      return "severe";
    default:
      return "informative";
  }
}

const useStyles = makeStyles({
  container: {
    display: "flex",
    gap: tokens.spacingHorizontalL,
    overflowX: "auto",
    paddingBottom: tokens.spacingVerticalM,
    minHeight: "300px",
  },
  waveColumn: {
    minWidth: "280px",
    maxWidth: "350px",
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
    backgroundColor: tokens.colorNeutralBackground2,
    borderRadius: tokens.borderRadiusMedium,
    padding: tokens.spacingVerticalM,
  },
  waveHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    paddingBottom: tokens.spacingVerticalS,
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
    marginBottom: tokens.spacingVerticalXS,
  },
  waveTitle: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
  },
  workloadCard: {
    cursor: "grab",
    padding: tokens.spacingVerticalS,
    marginBottom: tokens.spacingVerticalXS,
  },
  workloadCardDragging: {
    opacity: "0.5",
    cursor: "grabbing",
    padding: tokens.spacingVerticalS,
    marginBottom: tokens.spacingVerticalXS,
  },
  workloadRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  workloadMeta: {
    display: "flex",
    gap: tokens.spacingHorizontalXS,
    flexWrap: "wrap",
    marginTop: tokens.spacingVerticalXXS,
  },
  moveButtons: {
    display: "flex",
    flexDirection: "column",
    gap: "2px",
  },
  dropZone: {
    border: `2px dashed ${tokens.colorNeutralStroke1}`,
    borderRadius: tokens.borderRadiusMedium,
    padding: tokens.spacingVerticalM,
    textAlign: "center",
    minHeight: "60px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  dropZoneActive: {
    border: `2px dashed ${tokens.colorBrandStroke1}`,
    borderRadius: tokens.borderRadiusMedium,
    padding: tokens.spacingVerticalM,
    textAlign: "center",
    minHeight: "60px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: tokens.colorBrandBackground2,
  },
  warningBar: {
    marginBottom: tokens.spacingVerticalS,
  },
  emptyState: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "200px",
    padding: tokens.spacingVerticalXXL,
  },
});

interface WaveTimelineProps {
  waves: WaveResponse[];
  warnings?: ValidationWarning[];
  onMoveWorkload?: (workloadId: string, targetWaveId: string, position: number) => void;
  onReorder?: (waveId: string, workloadId: string, direction: "up" | "down") => void;
}

export default function WaveTimeline({
  waves,
  warnings = [],
  onMoveWorkload,
  onReorder,
}: WaveTimelineProps) {
  const styles = useStyles();
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dragOverWaveId, setDragOverWaveId] = useState<string | null>(null);

  const handleDragStart = useCallback(
    (e: React.DragEvent, workloadId: string) => {
      e.dataTransfer.setData("text/plain", workloadId);
      e.dataTransfer.effectAllowed = "move";
      setDraggingId(workloadId);
    },
    [],
  );

  const handleDragEnd = useCallback(() => {
    setDraggingId(null);
    setDragOverWaveId(null);
  }, []);

  const handleDragOver = useCallback(
    (e: React.DragEvent, waveId: string) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      setDragOverWaveId(waveId);
    },
    [],
  );

  const handleDragLeave = useCallback(() => {
    setDragOverWaveId(null);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent, targetWaveId: string) => {
      e.preventDefault();
      const workloadId = e.dataTransfer.getData("text/plain");
      setDraggingId(null);
      setDragOverWaveId(null);
      if (workloadId && onMoveWorkload) {
        onMoveWorkload(workloadId, targetWaveId, 0);
      }
    },
    [onMoveWorkload],
  );

  const handleMoveUp = useCallback(
    (waveId: string, workloadId: string) => {
      if (onReorder) {
        onReorder(waveId, workloadId, "up");
      }
    },
    [onReorder],
  );

  const handleMoveDown = useCallback(
    (waveId: string, workloadId: string) => {
      if (onReorder) {
        onReorder(waveId, workloadId, "down");
      }
    },
    [onReorder],
  );

  // Collect warnings per workload
  const workloadWarnings = new Map<string, ValidationWarning[]>();
  for (const w of warnings) {
    if (w.workload_id) {
      const existing = workloadWarnings.get(w.workload_id) ?? [];
      existing.push(w);
      workloadWarnings.set(w.workload_id, existing);
    }
  }

  if (waves.length === 0) {
    return (
      <div className={styles.emptyState} data-testid="wave-empty">
        <Body1>
          No waves generated yet. Click &quot;Generate Waves&quot; to create a
          migration plan.
        </Body1>
      </div>
    );
  }

  return (
    <div>
      {warnings.length > 0 && (
        <div data-testid="wave-warnings">
          {warnings.map((w, idx) => (
            <MessageBar
              key={`warn-${idx}`}
              intent="warning"
              className={styles.warningBar}
            >
              <MessageBarBody>
                <WarningRegular /> {w.message}
              </MessageBarBody>
            </MessageBar>
          ))}
        </div>
      )}

      <div className={styles.container} data-testid="wave-timeline">
        {waves.map((wave) => (
          <div
            key={wave.id}
            className={styles.waveColumn}
            onDragOver={(e) => handleDragOver(e, wave.id)}
            onDragLeave={handleDragLeave}
            onDrop={(e) => handleDrop(e, wave.id)}
            data-testid={`wave-column-${wave.id}`}
          >
            <div className={styles.waveHeader}>
              <div className={styles.waveTitle}>
                <Text weight="semibold">{wave.name}</Text>
                <Badge
                  appearance="filled"
                  color={statusColor(wave.status)}
                  size="small"
                >
                  {wave.status}
                </Badge>
              </div>
              <Caption1>{wave.workloads.length} workloads</Caption1>
            </div>

            {wave.workloads.map((wl: WaveWorkloadItem, idx: number) => {
              const wlWarnings = workloadWarnings.get(wl.workload_id) ?? [];
              return (
                <Card
                  key={wl.id}
                  className={
                    draggingId === wl.workload_id
                      ? styles.workloadCardDragging
                      : styles.workloadCard
                  }
                  draggable
                  onDragStart={(e) => handleDragStart(e, wl.workload_id)}
                  onDragEnd={handleDragEnd}
                  data-testid={`workload-card-${wl.workload_id}`}
                >
                  <CardHeader
                    header={
                      <div className={styles.workloadRow}>
                        <div>
                          <Text weight="semibold">{wl.name}</Text>
                          <div className={styles.workloadMeta}>
                            <Badge
                              appearance="tint"
                              color={criticalityColor(wl.criticality)}
                              size="small"
                            >
                              {wl.criticality}
                            </Badge>
                            <Badge appearance="outline" size="small">
                              {wl.migration_strategy}
                            </Badge>
                            <Badge appearance="outline" size="small">
                              {wl.type}
                            </Badge>
                          </div>
                          {wlWarnings.length > 0 &&
                            wlWarnings.map((warn, wIdx) => (
                              <MessageBar
                                key={`wl-warn-${wIdx}`}
                                intent="warning"
                                className={styles.warningBar}
                              >
                                <MessageBarBody>{warn.message}</MessageBarBody>
                              </MessageBar>
                            ))}
                        </div>
                        <div className={styles.moveButtons}>
                          <Tooltip content="Move up" relationship="label">
                            <Button
                              size="small"
                              icon={<ArrowUpRegular />}
                              appearance="subtle"
                              disabled={idx === 0}
                              onClick={() =>
                                handleMoveUp(wave.id, wl.workload_id)
                              }
                              aria-label={`Move ${wl.name} up`}
                            />
                          </Tooltip>
                          <Tooltip content="Move down" relationship="label">
                            <Button
                              size="small"
                              icon={<ArrowDownRegular />}
                              appearance="subtle"
                              disabled={idx === wave.workloads.length - 1}
                              onClick={() =>
                                handleMoveDown(wave.id, wl.workload_id)
                              }
                              aria-label={`Move ${wl.name} down`}
                            />
                          </Tooltip>
                        </div>
                      </div>
                    }
                  />
                </Card>
              );
            })}

            {wave.workloads.length === 0 && (
              <div
                className={
                  dragOverWaveId === wave.id
                    ? styles.dropZoneActive
                    : styles.dropZone
                }
              >
                <Caption1>Drop workloads here</Caption1>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
