import {
  Badge,
  Card,
  CardHeader,
  Text,
  makeStyles,
  mergeClasses,
  tokens,
} from "@fluentui/react-components";
import {
  AddRegular,
  DeleteRegular,
  EditRegular,
} from "@fluentui/react-icons";
import {
  Accordion,
  AccordionHeader,
  AccordionItem,
  AccordionPanel,
} from "@fluentui/react-components";
import type {
  EnhancedComponentChange,
  PropertyDiff,
  CategoryGroup,
} from "../../services/api";

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const useStyles = makeStyles({
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
  countBadge: {
    marginLeft: "4px",
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
// PropertyDiffRow
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// EnhancedChangeCard
// ---------------------------------------------------------------------------

interface EnhancedChangeCardProps {
  comp: EnhancedComponentChange;
  type: "added" | "removed" | "modified";
}

function EnhancedChangeCard({ comp, type }: EnhancedChangeCardProps) {
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

// ---------------------------------------------------------------------------
// CategorySection
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Inline flat view (no categories)
// ---------------------------------------------------------------------------

interface VersionDiffInlineViewProps {
  addedComponents: EnhancedComponentChange[];
  removedComponents: EnhancedComponentChange[];
  modifiedComponents: EnhancedComponentChange[];
  categoryGroups: CategoryGroup[];
}

export default function VersionDiffInlineView({
  addedComponents,
  removedComponents,
  modifiedComponents,
  categoryGroups,
}: VersionDiffInlineViewProps) {
  const styles = useStyles();
  const hasCategories = categoryGroups && categoryGroups.length > 0;

  if (hasCategories) {
    return (
      <Accordion
        multiple
        collapsible
        defaultOpenItems={categoryGroups.map((g) => g.category)}
      >
        {categoryGroups.map((group) => (
          <CategorySection key={group.category} group={group} />
        ))}
      </Accordion>
    );
  }

  return (
    <>
      {addedComponents.length > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionTitle}>
            <AddRegular />
            <Text>Added</Text>
            <Badge
              appearance="filled"
              color="success"
              className={styles.countBadge}
            >
              {addedComponents.length}
            </Badge>
          </div>
          {addedComponents.map((c) => (
            <EnhancedChangeCard
              key={c.name}
              comp={c}
              type="added"
            />
          ))}
        </div>
      )}

      {removedComponents.length > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionTitle}>
            <DeleteRegular />
            <Text>Removed</Text>
            <Badge
              appearance="filled"
              color="danger"
              className={styles.countBadge}
            >
              {removedComponents.length}
            </Badge>
          </div>
          {removedComponents.map((c) => (
            <EnhancedChangeCard
              key={c.name}
              comp={c}
              type="removed"
            />
          ))}
        </div>
      )}

      {modifiedComponents.length > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionTitle}>
            <EditRegular />
            <Text>Modified</Text>
            <Badge
              appearance="filled"
              color="warning"
              className={styles.countBadge}
            >
              {modifiedComponents.length}
            </Badge>
          </div>
          {modifiedComponents.map((c) => (
            <EnhancedChangeCard
              key={c.name}
              comp={c}
              type="modified"
            />
          ))}
        </div>
      )}
    </>
  );
}
