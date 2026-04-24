import {
  Badge,
  Button,
  Spinner,
  Text,
  ToggleButton,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  ArrowBidirectionalLeftRightRegular,
  ArrowUndoRegular,
  SplitHorizontalRegular,
  TextAlignLeftRegular,
} from "@fluentui/react-icons";
import { useCallback, useEffect, useState } from "react";
import type { EnhancedVersionDiffResult } from "../../services/api";
import { api } from "../../services/api";
import VersionDiffSideBySide from "./VersionDiffSideBySide";
import VersionDiffInlineView from "./VersionDiffInlineView";

export interface VersionDiffProps {
  architectureId: string;
  fromVersion: number;
  toVersion: number;
  onRestore?: (version: number) => void;
}

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: "16px",
    paddingTop: "16px",
    paddingRight: "16px",
    paddingBottom: "16px",
    paddingLeft: "16px",
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    marginBottom: "8px",
  },
  headerActions: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    marginLeft: "auto",
  },
  versionRange: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  changeSummaryHeader: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    paddingTop: "12px",
    paddingRight: "12px",
    paddingBottom: "12px",
    paddingLeft: "12px",
    backgroundColor: tokens.colorNeutralBackground3,
    borderRadius: tokens.borderRadiusMedium,
    flexWrap: "wrap",
  },
  emptyState: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "8px",
    paddingTop: "32px",
    paddingRight: "32px",
    paddingBottom: "32px",
    paddingLeft: "32px",
    color: tokens.colorNeutralForeground3,
  },
  errorText: {
    color: tokens.colorPaletteRedForeground1,
    paddingTop: "8px",
    paddingRight: "8px",
    paddingBottom: "8px",
    paddingLeft: "8px",
  },
});

export default function VersionDiff({
  architectureId,
  fromVersion,
  toVersion,
  onRestore,
}: VersionDiffProps) {
  const styles = useStyles();
  const [diff, setDiff] = useState<EnhancedVersionDiffResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"inline" | "side-by-side">(
    "inline",
  );

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
      setError(
        err instanceof Error ? err.message : "Failed to load diff",
      );
    } finally {
      setLoading(false);
    }
  }, [architectureId, fromVersion, toVersion]);

  useEffect(() => {
    void fetchDiff();
  }, [fetchDiff]);

  if (loading) {
    return (
      <div
        className={styles.container}
        aria-label="Version diff loading"
      >
        <Spinner label="Computing diff…" size="small" />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <Text className={styles.errorText} role="alert">
          {error}
        </Text>
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
      {/* Header */}
      <div className={styles.header}>
        <ArrowBidirectionalLeftRightRegular fontSize={20} />
        <Text weight="semibold" size={400}>
          Version Diff
        </Text>
        <div className={styles.headerActions}>
          <ToggleButton
            appearance="subtle"
            icon={<TextAlignLeftRegular />}
            checked={viewMode === "inline"}
            onClick={() => setViewMode("inline")}
            size="small"
            data-testid="view-inline"
          >
            Inline
          </ToggleButton>
          <ToggleButton
            appearance="subtle"
            icon={<SplitHorizontalRegular />}
            checked={viewMode === "side-by-side"}
            onClick={() => setViewMode("side-by-side")}
            size="small"
            data-testid="view-side-by-side"
          >
            Side-by-side
          </ToggleButton>
          {onRestore && (
            <Button
              appearance="secondary"
              icon={<ArrowUndoRegular />}
              onClick={() => onRestore(fromVersion)}
              size="small"
              data-testid="revert-button"
            >
              Revert to v{fromVersion}
            </Button>
          )}
        </div>
      </div>

      {/* Version range */}
      <div className={styles.versionRange}>
        <Badge appearance="outline" color="brand">
          v{diff.from_version}
        </Badge>
        <Text>→</Text>
        <Badge appearance="outline" color="brand">
          v{diff.to_version}
        </Badge>
      </div>

      {/* Change summary header with counts */}
      <div className={styles.changeSummaryHeader}>
        <Text weight="semibold">{diff.summary}</Text>
        {diff.change_counts && (
          <>
            {diff.change_counts.added > 0 && (
              <Badge appearance="filled" color="success">
                +{diff.change_counts.added}
              </Badge>
            )}
            {diff.change_counts.removed > 0 && (
              <Badge appearance="filled" color="danger">
                −{diff.change_counts.removed}
              </Badge>
            )}
            {diff.change_counts.modified > 0 && (
              <Badge appearance="filled" color="warning">
                ~{diff.change_counts.modified}
              </Badge>
            )}
          </>
        )}
      </div>

      {totalChanges === 0 ? (
        <div className={styles.emptyState}>
          <Text>No differences found between these versions.</Text>
        </div>
      ) : viewMode === "side-by-side" ? (
        <VersionDiffSideBySide diff={diff} />
      ) : (
        <VersionDiffInlineView
          addedComponents={diff.added_components}
          removedComponents={diff.removed_components}
          modifiedComponents={diff.modified_components}
          categoryGroups={diff.category_groups}
        />
      )}
    </div>
  );
}
