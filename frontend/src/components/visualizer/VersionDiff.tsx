import {
  Accordion,
  AccordionHeader,
  AccordionItem,
  AccordionPanel,
  Badge,
  Button,
  Card,
  CardHeader,
  makeStyles,
  mergeClasses,
  Spinner,
  Text,
  ToggleButton,
  tokens,
} from "@fluentui/react-components";
import {
  AddRegular,
  ArrowBidirectionalLeftRightRegular,
  ArrowUndoRegular,
  DeleteRegular,
  EditRegular,
  SplitHorizontalRegular,
  TextAlignLeftRegular,
} from "@fluentui/react-icons";
import { useCallback, useEffect, useState } from "react";
import type {
  EnhancedComponentChange,
  EnhancedVersionDiffResult,
  PropertyDiff,
  CategoryGroup,
} from "../../services/api";
import { api } from "../../services/api";

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
    padding: "16px",
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
    padding: "12px",
    backgroundColor: tokens.colorNeutralBackground3,
    borderRadius: tokens.borderRadiusMedium,
    flexWrap: "wrap",
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
  sideBySide: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "16px",
  },
  sideColumn: {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  },
  sideColumnHeader: {
    fontWeight: tokens.fontWeightSemibold,
    padding: "4px 0",
  },
  propertyDiffs: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
    marginTop: "8px",
    padding: "8px",
    backgroundColor: tokens.colorNeutralBackground2,
    borderRadius: tokens.borderRadiusSmall,
    fontSize: tokens.fontSizeBase200,
  },
  propRow: {
    display: "flex",
    gap: "8px",
    alignItems: "baseline",
  },
  propName: {
    fontWeight: tokens.fontWeightSemibold,
    minWidth: "100px",
  },
  propAdded: {
    color: tokens.colorPaletteGreenForeground1,
  },
  propRemoved: {
    color: tokens.colorPaletteRedForeground1,
    textDecorationLine: "line-through",
  },
  propModifiedOld: {
    color: tokens.colorPaletteRedForeground1,
    textDecorationLine: "line-through",
  },
  propModifiedNew: {
    color: tokens.colorPaletteGreenForeground1,
  },
  restoreButton: {
    marginLeft: "auto",
  },
});

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function PropertyDiffRow({ diff }: { diff: PropertyDiff }) {
  const styles = useStyles();

  return (
    <div className={styles.propRow}>
      <Text className={styles.propName}>{diff.property_name}</Text>
      {diff.change_type === "added" && (
        <Text className={styles.propAdded}>
          + {formatValue(diff.new_value)}
        </Text>
      )}
      {diff.change_type === "removed" && (
        <Text className={styles.propRemoved}>
          {formatValue(diff.old_value)}
        </Text>
      )}
      {diff.change_type === "modified" && (
        <>
          <Text className={styles.propModifiedOld}>
            {formatValue(diff.old_value)}
          </Text>
          <Text>→</Text>
          <Text className={styles.propModifiedNew}>
            {formatValue(diff.new_value)}
          </Text>
        </>
      )}
    </div>
  );
}

function EnhancedChangeCard({
  comp,
  type,
}: {
  comp: EnhancedComponentChange;
  type: "added" | "removed" | "modified";
}) {
  const styles = useStyles();
  const cardClass = mergeClasses(
    styles.changeCard,
    type === "added"
      ? styles.addedCard
      : type === "removed"
        ? styles.removedCard
        : styles.modifiedCard,
  );

  return (
    <Card className={cardClass}>
      <CardHeader
        header={
          <div>
            <Text className={styles.changeName}>{comp.name}</Text>
            {comp.detail && (
              <Text className={styles.changeDetail} block>
                {comp.detail}
              </Text>
            )}
          </div>
        }
      />
      {comp.property_diffs && comp.property_diffs.length > 0 && (
        <div className={styles.propertyDiffs} data-testid="property-diffs">
          {comp.property_diffs.map((pd, idx) => (
            <PropertyDiffRow key={`${pd.property_name}-${idx}`} diff={pd} />
          ))}
        </div>
      )}
    </Card>
  );
}

function CategorySection({ group }: { group: CategoryGroup }) {
  const styles = useStyles();
  const totalChanges =
    group.added.length + group.removed.length + group.modified.length;

  return (
    <AccordionItem value={group.category}>
      <AccordionHeader>
        <div className={styles.sectionTitle}>
          <Text>{group.display_name}</Text>
          <Badge appearance="tint" color="informative">
            {totalChanges}
          </Badge>
        </div>
      </AccordionHeader>
      <AccordionPanel>
        <div className={styles.section}>
          {group.added.length > 0 && (
            <div className={styles.section}>
              <div className={styles.sectionTitle}>
                <AddRegular />
                <Text>Added</Text>
                <Badge
                  appearance="filled"
                  color="success"
                  className={styles.countBadge}
                >
                  {group.added.length}
                </Badge>
              </div>
              {group.added.map((c) => (
                <EnhancedChangeCard
                  key={c.name}
                  comp={c}
                  type="added"
                />
              ))}
            </div>
          )}
          {group.removed.length > 0 && (
            <div className={styles.section}>
              <div className={styles.sectionTitle}>
                <DeleteRegular />
                <Text>Removed</Text>
                <Badge
                  appearance="filled"
                  color="danger"
                  className={styles.countBadge}
                >
                  {group.removed.length}
                </Badge>
              </div>
              {group.removed.map((c) => (
                <EnhancedChangeCard
                  key={c.name}
                  comp={c}
                  type="removed"
                />
              ))}
            </div>
          )}
          {group.modified.length > 0 && (
            <div className={styles.section}>
              <div className={styles.sectionTitle}>
                <EditRegular />
                <Text>Modified</Text>
                <Badge
                  appearance="filled"
                  color="warning"
                  className={styles.countBadge}
                >
                  {group.modified.length}
                </Badge>
              </div>
              {group.modified.map((c) => (
                <EnhancedChangeCard
                  key={c.name}
                  comp={c}
                  type="modified"
                />
              ))}
            </div>
          )}
        </div>
      </AccordionPanel>
    </AccordionItem>
  );
}

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

  const hasCategories =
    diff.category_groups && diff.category_groups.length > 0;

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
        /* Side-by-side view */
        <div className={styles.sideBySide} data-testid="side-by-side-view">
          <div className={styles.sideColumn}>
            <Text className={styles.sideColumnHeader}>
              v{diff.from_version} (Before)
            </Text>
            {diff.removed_components.map((c) => (
              <EnhancedChangeCard
                key={c.name}
                comp={c}
                type="removed"
              />
            ))}
            {diff.modified_components.map((c) => (
              <Card
                key={c.name}
                className={mergeClasses(
                  styles.changeCard,
                  styles.modifiedCard,
                )}
              >
                <CardHeader
                  header={
                    <div>
                      <Text className={styles.changeName}>
                        {c.name}
                      </Text>
                      <Text className={styles.changeDetail} block>
                        Before modification
                      </Text>
                    </div>
                  }
                />
                {c.property_diffs?.filter(
                  (pd) =>
                    pd.change_type === "modified" ||
                    pd.change_type === "removed",
                ).map((pd, idx) => (
                  <div
                    key={`${pd.property_name}-${idx}`}
                    className={styles.propRow}
                    style={{ padding: "4px 12px" }}
                  >
                    <Text className={styles.propName}>
                      {pd.property_name}
                    </Text>
                    <Text className={styles.propModifiedOld}>
                      {formatValue(pd.old_value)}
                    </Text>
                  </div>
                ))}
              </Card>
            ))}
          </div>
          <div className={styles.sideColumn}>
            <Text className={styles.sideColumnHeader}>
              v{diff.to_version} (After)
            </Text>
            {diff.added_components.map((c) => (
              <EnhancedChangeCard
                key={c.name}
                comp={c}
                type="added"
              />
            ))}
            {diff.modified_components.map((c) => (
              <Card
                key={c.name}
                className={mergeClasses(
                  styles.changeCard,
                  styles.modifiedCard,
                )}
              >
                <CardHeader
                  header={
                    <div>
                      <Text className={styles.changeName}>
                        {c.name}
                      </Text>
                      <Text className={styles.changeDetail} block>
                        After modification
                      </Text>
                    </div>
                  }
                />
                {c.property_diffs?.filter(
                  (pd) =>
                    pd.change_type === "modified" ||
                    pd.change_type === "added",
                ).map((pd, idx) => (
                  <div
                    key={`${pd.property_name}-${idx}`}
                    className={styles.propRow}
                    style={{ padding: "4px 12px" }}
                  >
                    <Text className={styles.propName}>
                      {pd.property_name}
                    </Text>
                    <Text className={styles.propModifiedNew}>
                      {formatValue(pd.new_value)}
                    </Text>
                  </div>
                ))}
              </Card>
            ))}
          </div>
        </div>
      ) : hasCategories ? (
        /* Inline category-grouped view */
        <Accordion
          multiple
          collapsible
          defaultOpenItems={diff.category_groups.map(
            (g) => g.category,
          )}
        >
          {diff.category_groups.map((group) => (
            <CategorySection key={group.category} group={group} />
          ))}
        </Accordion>
      ) : (
        /* Inline flat view (fallback) */
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
                <EnhancedChangeCard
                  key={c.name}
                  comp={c}
                  type="added"
                />
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
                <EnhancedChangeCard
                  key={c.name}
                  comp={c}
                  type="removed"
                />
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
                <EnhancedChangeCard
                  key={c.name}
                  comp={c}
                  type="modified"
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
