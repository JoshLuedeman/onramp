import {
  Badge,
  Button,
  Card,
  CardHeader,
  makeStyles,
  Spinner,
  Text,
  tokens,
  Tooltip,
} from "@fluentui/react-components";
import {
  ArrowResetRegular,
  ClockRegular,
  EyeRegular,
  HistoryRegular,
  PersonRegular,
} from "@fluentui/react-icons";
import { useCallback, useEffect, useState } from "react";
import type { ArchitectureVersionItem } from "../../services/api";
import { api } from "../../services/api";

export interface VersionHistoryProps {
  architectureId: string;
  onViewVersion?: (version: ArchitectureVersionItem) => void;
  onRestoreVersion?: (version: ArchitectureVersionItem) => void;
}

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: "16px",
    padding: "16px",
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    marginBottom: "8px",
  },
  timeline: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  versionCard: {
    padding: "12px 16px",
  },
  versionHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "12px",
  },
  versionInfo: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
    flex: 1,
    minWidth: 0,
  },
  versionTitle: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  meta: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    color: tokens.colorNeutralForeground3,
    fontSize: tokens.fontSizeBase200,
  },
  metaItem: {
    display: "flex",
    alignItems: "center",
    gap: "4px",
  },
  actions: {
    display: "flex",
    gap: "8px",
    flexShrink: 0,
  },
  emptyState: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "8px",
    padding: "32px",
    color: tokens.colorNeutralForeground3,
  },
  errorText: {
    color: tokens.colorPaletteRedForeground1,
    padding: "8px",
  },
});

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function VersionHistory({
  architectureId,
  onViewVersion,
  onRestoreVersion,
}: VersionHistoryProps) {
  const styles = useStyles();
  const [versions, setVersions] = useState<ArchitectureVersionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [restoringId, setRestoringId] = useState<string | null>(null);

  const fetchVersions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.architectureVersions.list(architectureId);
      setVersions(data.versions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load versions");
    } finally {
      setLoading(false);
    }
  }, [architectureId]);

  useEffect(() => {
    void fetchVersions();
  }, [fetchVersions]);

  const handleRestore = useCallback(
    async (version: ArchitectureVersionItem) => {
      setRestoringId(version.id);
      try {
        const restored = await api.architectureVersions.restore(
          architectureId,
          version.version_number,
        );
        onRestoreVersion?.(restored);
        await fetchVersions();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Restore failed");
      } finally {
        setRestoringId(null);
      }
    },
    [architectureId, fetchVersions, onRestoreVersion],
  );

  if (loading) {
    return (
      <div className={styles.container} aria-label="Version history loading">
        <Spinner label="Loading version history…" size="small" />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <Text className={styles.errorText} role="alert">{error}</Text>
      </div>
    );
  }

  return (
    <div className={styles.container} aria-label="Version history">
      <div className={styles.header}>
        <HistoryRegular fontSize={20} />
        <Text weight="semibold" size={400}>
          Version History
        </Text>
        <Badge appearance="filled" color="informative">
          {versions.length}
        </Badge>
      </div>

      {versions.length === 0 ? (
        <div className={styles.emptyState}>
          <HistoryRegular fontSize={32} />
          <Text>No versions recorded yet.</Text>
        </div>
      ) : (
        <div className={styles.timeline} role="list" aria-label="Architecture versions">
          {versions.map((v) => (
            <Card key={v.id} className={styles.versionCard} role="listitem">
              <CardHeader
                header={
                  <div className={styles.versionHeader}>
                    <div className={styles.versionInfo}>
                      <div className={styles.versionTitle}>
                        <Badge appearance="outline" color="brand">
                          v{v.version_number}
                        </Badge>
                        <Text weight="semibold">
                          {v.change_summary ?? `Version ${v.version_number}`}
                        </Text>
                      </div>
                      <div className={styles.meta}>
                        <span className={styles.metaItem}>
                          <ClockRegular fontSize={14} />
                          {formatTimestamp(v.created_at)}
                        </span>
                        {v.created_by && (
                          <span className={styles.metaItem}>
                            <PersonRegular fontSize={14} />
                            {v.created_by}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className={styles.actions}>
                      <Tooltip content="View this version" relationship="label">
                        <Button
                          icon={<EyeRegular />}
                          appearance="subtle"
                          size="small"
                          aria-label={`View version ${v.version_number}`}
                          onClick={() => onViewVersion?.(v)}
                        />
                      </Tooltip>
                      <Tooltip content="Restore this version" relationship="label">
                        <Button
                          icon={
                            restoringId === v.id ? (
                              <Spinner size="tiny" />
                            ) : (
                              <ArrowResetRegular />
                            )
                          }
                          appearance="subtle"
                          size="small"
                          aria-label={`Restore version ${v.version_number}`}
                          disabled={restoringId !== null}
                          onClick={() => void handleRestore(v)}
                        />
                      </Tooltip>
                    </div>
                  </div>
                }
              />
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
