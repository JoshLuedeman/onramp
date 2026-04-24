import { Text, makeStyles, tokens } from "@fluentui/react-components";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface DependencyGraphLegendProps {
  criticalityColors: Record<string, string>;
  groupPaletteSample: string;
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const useStyles = makeStyles({
  legend: {
    display: "flex",
    gap: tokens.spacingHorizontalL,
    flexWrap: "wrap",
    alignItems: "center",
  },
  legendItem: {
    display: "flex",
    gap: tokens.spacingHorizontalXS,
    alignItems: "center",
  },
  legendSwatch: {
    width: "16px",
    height: "16px",
    borderRadius: tokens.borderRadiusSmall,
  },
  legendSwatchCycle: {
    width: "16px",
    height: "16px",
    borderRadius: tokens.borderRadiusSmall,
    backgroundColor: tokens.colorStatusDangerForeground1,
    borderTopWidth: "2px",
    borderRightWidth: "2px",
    borderBottomWidth: "2px",
    borderLeftWidth: "2px",
    borderTopStyle: "solid",
    borderRightStyle: "solid",
    borderBottomStyle: "solid",
    borderLeftStyle: "solid",
    borderTopColor: tokens.colorStatusDangerForeground1,
    borderRightColor: tokens.colorStatusDangerForeground1,
    borderBottomColor: tokens.colorStatusDangerForeground1,
    borderLeftColor: tokens.colorStatusDangerForeground1,
  },
});

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DependencyGraphLegend({
  criticalityColors,
  groupPaletteSample,
}: DependencyGraphLegendProps) {
  const styles = useStyles();

  return (
    <div className={styles.legend}>
      {Object.entries(criticalityColors).map(([level, color]) => (
        <div key={level} className={styles.legendItem}>
          <div
            className={styles.legendSwatch}
            style={{ backgroundColor: color }}
            aria-hidden="true"
          />
          <Text size={200}>{level}</Text>
        </div>
      ))}
      <div className={styles.legendItem}>
        <div
          className={styles.legendSwatchCycle}
          aria-hidden="true"
        />
        <Text size={200}>circular dependency</Text>
      </div>
      <div className={styles.legendItem}>
        <div
          className={styles.legendSwatch}
          style={{ backgroundColor: groupPaletteSample }}
          aria-hidden="true"
        />
        <Text size={200}>migration group</Text>
      </div>
    </div>
  );
}
