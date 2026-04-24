import {
  Card,
  CardHeader,
  Text,
  makeStyles,
  mergeClasses,
  tokens,
} from "@fluentui/react-components";
import type {
  EnhancedComponentChange,
  EnhancedVersionDiffResult,
} from "../../services/api";

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const useStyles = makeStyles({
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
    paddingTop: "4px",
    paddingBottom: "4px",
  },
  changeCard: {
    paddingTop: "8px",
    paddingRight: "12px",
    paddingBottom: "8px",
    paddingLeft: "12px",
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
  propRow: {
    display: "flex",
    gap: "8px",
    alignItems: "baseline",
  },
  propName: {
    fontWeight: tokens.fontWeightSemibold,
    minWidth: "100px",
  },
  propModifiedOld: {
    color: tokens.colorPaletteRedForeground1,
    textDecorationLine: "line-through",
  },
  propModifiedNew: {
    color: tokens.colorPaletteGreenForeground1,
  },
  propertyDiffs: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
    marginTop: "8px",
    paddingTop: "8px",
    paddingRight: "8px",
    paddingBottom: "8px",
    paddingLeft: "8px",
    backgroundColor: tokens.colorNeutralBackground2,
    borderRadius: tokens.borderRadiusSmall,
    fontSize: tokens.fontSizeBase200,
  },
  sideBySidePropRow: {
    paddingTop: tokens.spacingVerticalXS,
    paddingRight: tokens.spacingHorizontalM,
    paddingBottom: tokens.spacingVerticalXS,
    paddingLeft: tokens.spacingHorizontalM,
  },
  propAdded: {
    color: tokens.colorPaletteGreenForeground1,
  },
  propRemoved: {
    color: tokens.colorPaletteRedForeground1,
    textDecorationLine: "line-through",
  },
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

// ---------------------------------------------------------------------------
// Internal change card for side-by-side (added/removed)
// ---------------------------------------------------------------------------

function SideBySideChangeCard({
  comp,
  type,
}: {
  comp: EnhancedComponentChange;
  type: "added" | "removed";
}) {
  const styles = useStyles();
  const cardClass = mergeClasses(
    styles.changeCard,
    type === "added" ? styles.addedCard : styles.removedCard,
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
            <div key={`${pd.property_name}-${idx}`} className={styles.propRow}>
              <Text className={styles.propName}>{pd.property_name}</Text>
              {pd.change_type === "added" && (
                <Text className={styles.propAdded}>+ {formatValue(pd.new_value)}</Text>
              )}
              {pd.change_type === "removed" && (
                <Text className={styles.propRemoved}>{formatValue(pd.old_value)}</Text>
              )}
              {pd.change_type === "modified" && (
                <>
                  <Text className={styles.propModifiedOld}>{formatValue(pd.old_value)}</Text>
                  <Text>→</Text>
                  <Text className={styles.propModifiedNew}>{formatValue(pd.new_value)}</Text>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface VersionDiffSideBySideProps {
  diff: EnhancedVersionDiffResult;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function VersionDiffSideBySide({ diff }: VersionDiffSideBySideProps) {
  const styles = useStyles();

  return (
    <div className={styles.sideBySide} data-testid="side-by-side-view">
      <div className={styles.sideColumn}>
        <Text className={styles.sideColumnHeader}>
          v{diff.from_version} (Before)
        </Text>
        {diff.removed_components.map((c) => (
          <SideBySideChangeCard
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
                className={`${styles.propRow} ${styles.sideBySidePropRow}`}
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
          <SideBySideChangeCard
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
                className={`${styles.propRow} ${styles.sideBySidePropRow}`}
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
  );
}
