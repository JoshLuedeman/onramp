import {
  Badge,
  Card,
  CardHeader,
  makeStyles,
  Spinner,
  Text,
  tokens,
} from "@fluentui/react-components";
import {
  AddRegular,
  ArrowBidirectionalLeftRightRegular,
  DeleteRegular,
  EditRegular,
} from "@fluentui/react-icons";
import { useCallback, useEffect, useState } from "react";
import type { VersionDiffResult } from "../../services/api";
import { api } from "../../services/api";

export interface VersionDiffProps {
  architectureId: string;
  fromVersion: number;
  toVersion: number;
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
  versionRange: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  section: {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  },
  sectionTitle: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    fontWeight: tokens.fontWeightSemibold,
  },
  changeCard: {
    padding: "8px 12px",
  },
  addedCard: {
    borderLeftWidth: "3px",
    borderLeftStyle: "solid",
    borderLeftColor: tokens.colorPaletteGreenBorder1,
  },
  removedCard: {
    borderLeftWidth: "3px",
    borderLeftStyle: "solid",
    borderLeftColor: tokens.colorPaletteRedBorder1,
  },
  modifiedCard: {
    borderLeftWidth: "3px",
    borderLeftStyle: "solid",
    borderLeftColor: tokens.colorPaletteYellowBorder1,
  },
  changeName: {
    fontWeight: tokens.fontWeightSemibold,
  },
  changeDetail: {
    color: tokens.colorNeutralForeground3,
    fontSize: tokens.fontSizeBase200,
  },
  summary: {
    padding: "12px",
    backgroundColor: tokens.colorNeutralBackground3,
    borderRadius: tokens.borderRadiusMedium,
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
  countBadge: {
    marginLeft: "4px",
  },
});

export default function VersionDiff({
  architectureId,
  fromVersion,
  toVersion,
}: VersionDiffProps) {
  const styles = useStyles();
  const [diff, setDiff] = useState<VersionDiffResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDiff = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.architectureVersions.diff(
        architectureId,
        fromVersion,
        toVersion,
      );
      setDiff(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load diff");
    } finally {
      setLoading(false);
    }
  }, [architectureId, fromVersion, toVersion]);

  useEffect(() => {
    void fetchDiff();
  }, [fetchDiff]);

  if (loading) {
    return (
      <div className={styles.container} aria-label="Version diff loading">
        <Spinner label="Computing diff…" size="small" />
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

  if (!diff) return null;

  const totalChanges =
    diff.added_components.length +
    diff.removed_components.length +
    diff.modified_components.length;

  return (
    <div className={styles.container} aria-label="Version diff">
      <div className={styles.header}>
        <ArrowBidirectionalLeftRightRegular fontSize={20} />
        <Text weight="semibold" size={400}>
          Version Diff
        </Text>
      </div>

      <div className={styles.versionRange}>
        <Badge appearance="outline" color="brand">v{diff.from_version}</Badge>
        <Text>→</Text>
        <Badge appearance="outline" color="brand">v{diff.to_version}</Badge>
      </div>

      <div className={styles.summary}>
        <Text>{diff.summary}</Text>
      </div>

      {totalChanges === 0 ? (
        <div className={styles.emptyState}>
          <Text>No differences found between these versions.</Text>
        </div>
      ) : (
        <>
          {diff.added_components.length > 0 && (
            <div className={styles.section}>
              <div className={styles.sectionTitle}>
                <AddRegular />
                <Text>Added</Text>
                <Badge
                  appearance="filled"
                  color="success"
                  className={styles.countBadge}
                >
                  {diff.added_components.length}
                </Badge>
              </div>
              {diff.added_components.map((c) => (
                <Card
                  key={c.name}
                  className={`${styles.changeCard} ${styles.addedCard}`}
                >
                  <CardHeader
                    header={
                      <div>
                        <Text className={styles.changeName}>{c.name}</Text>
                        {c.detail && (
                          <Text className={styles.changeDetail} block>
                            {c.detail}
                          </Text>
                        )}
                      </div>
                    }
                  />
                </Card>
              ))}
            </div>
          )}

          {diff.removed_components.length > 0 && (
            <div className={styles.section}>
              <div className={styles.sectionTitle}>
                <DeleteRegular />
                <Text>Removed</Text>
                <Badge
                  appearance="filled"
                  color="danger"
                  className={styles.countBadge}
                >
                  {diff.removed_components.length}
                </Badge>
              </div>
              {diff.removed_components.map((c) => (
                <Card
                  key={c.name}
                  className={`${styles.changeCard} ${styles.removedCard}`}
                >
                  <CardHeader
                    header={
                      <div>
                        <Text className={styles.changeName}>{c.name}</Text>
                        {c.detail && (
                          <Text className={styles.changeDetail} block>
                            {c.detail}
                          </Text>
                        )}
                      </div>
                    }
                  />
                </Card>
              ))}
            </div>
          )}

          {diff.modified_components.length > 0 && (
            <div className={styles.section}>
              <div className={styles.sectionTitle}>
                <EditRegular />
                <Text>Modified</Text>
                <Badge
                  appearance="filled"
                  color="warning"
                  className={styles.countBadge}
                >
                  {diff.modified_components.length}
                </Badge>
              </div>
              {diff.modified_components.map((c) => (
                <Card
                  key={c.name}
                  className={`${styles.changeCard} ${styles.modifiedCard}`}
                >
                  <CardHeader
                    header={
                      <div>
                        <Text className={styles.changeName}>{c.name}</Text>
                        {c.detail && (
                          <Text className={styles.changeDetail} block>
                            {c.detail}
                          </Text>
                        )}
                      </div>
                    }
                  />
                </Card>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
