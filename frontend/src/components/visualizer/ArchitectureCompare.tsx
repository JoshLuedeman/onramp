/**
 * ArchitectureCompare — side-by-side comparison of architecture variants.
 *
 * Renders three variant cards (cost-optimised, balanced, enterprise-grade)
 * with resource counts, cost ranges, complexity badges, compliance scores,
 * and a "Use this architecture" action.  The balanced variant is annotated
 * with a "Recommended" badge.  A trade-off analysis paragraph is shown
 * beneath the grid.
 *
 * Uses proper table semantics for WCAG 2.1 AA compliance.
 */

import {
  Badge,
  Body1,
  Button,
  Card,
  Spinner,
  Text,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  CheckmarkCircleRegular,
} from "@fluentui/react-icons";
import type { ArchitectureVariant, ComparisonResult } from "../../services/api";

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const useStyles = makeStyles({
  root: {
    marginTop: "24px",
  },
  loading: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "48px 0",
    gap: "12px",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    marginTop: "16px",
  },
  th: {
    padding: "12px 16px",
    textAlign: "left",
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase400,
    borderBottomColor: tokens.colorNeutralStroke1,
    borderBottomWidth: "2px",
    borderBottomStyle: "solid",
    verticalAlign: "top",
  },
  thSelected: {
    backgroundColor: tokens.colorBrandBackground2,
    borderTopColor: tokens.colorBrandStroke1,
    borderTopWidth: "2px",
    borderTopStyle: "solid",
    borderLeftColor: tokens.colorBrandStroke1,
    borderLeftWidth: "2px",
    borderLeftStyle: "solid",
    borderRightColor: tokens.colorBrandStroke1,
    borderRightWidth: "2px",
    borderRightStyle: "solid",
  },
  td: {
    padding: "10px 16px",
    borderBottomColor: tokens.colorNeutralStroke2,
    borderBottomWidth: "1px",
    borderBottomStyle: "solid",
    verticalAlign: "top",
  },
  tdSelected: {
    backgroundColor: tokens.colorBrandBackground2,
    borderLeftColor: tokens.colorBrandStroke1,
    borderLeftWidth: "2px",
    borderLeftStyle: "solid",
    borderRightColor: tokens.colorBrandStroke1,
    borderRightWidth: "2px",
    borderRightStyle: "solid",
  },
  metricLabel: {
    color: tokens.colorNeutralForeground3,
    fontWeight: tokens.fontWeightSemibold,
    padding: "10px 16px",
    borderBottomColor: tokens.colorNeutralStroke2,
    borderBottomWidth: "1px",
    borderBottomStyle: "solid",
    minWidth: "120px",
  },
  tradeoffSection: {
    marginTop: "24px",
    padding: "16px",
  },
  tradeoffTitle: {
    fontWeight: tokens.fontWeightSemibold,
    marginBottom: "8px",
  },
  badgeContainer: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  complianceList: {
    listStyle: "none",
    padding: 0,
    margin: 0,
  },
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const complexityColor = (c: string): "informative" | "warning" | "danger" => {
  if (c === "simple") return "informative";
  if (c === "complex") return "danger";
  return "warning";
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ArchitectureCompareProps {
  /** Comparison result from the API. */
  comparison: ComparisonResult | null;
  /** Whether data is currently loading. */
  loading?: boolean;
  /** Callback when the user selects a variant. */
  onSelectVariant?: (variant: ArchitectureVariant, index: number) => void;
  /** Currently selected variant index (-1 or undefined = none). */
  selectedIndex?: number;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ArchitectureCompare({
  comparison,
  loading = false,
  onSelectVariant,
  selectedIndex = -1,
}: ArchitectureCompareProps) {
  const styles = useStyles();

  if (loading) {
    return (
      <div className={styles.loading} data-testid="compare-loading">
        <Spinner size="medium" />
        <Text>Generating architecture variants…</Text>
      </div>
    );
  }

  if (!comparison || comparison.variants.length === 0) {
    return null;
  }

  // Gather all compliance frameworks across variants
  const allFrameworks = Array.from(
    new Set(
      comparison.variants.flatMap((v) => Object.keys(v.compliance_scores)),
    ),
  );

  return (
    <div className={styles.root} data-testid="architecture-compare" aria-label="Architecture comparison">
      <table className={styles.table} aria-label="Architecture variant comparison">
        <thead>
          <tr>
            <th scope="col" className={styles.metricLabel}>Metric</th>
            {comparison.variants.map((variant, idx) => {
              const isRecommended = idx === comparison.recommended_index;
              const isSelected = idx === selectedIndex;
              return (
                <th
                  key={variant.name}
                  scope="col"
                  className={`${styles.th} ${isSelected ? styles.thSelected : ""}`}
                  aria-selected={isSelected}
                  data-testid={`variant-header-${idx}`}
                >
                  <div className={styles.badgeContainer}>
                    <span>{variant.name}</span>
                    {isRecommended && (
                      <Badge
                        appearance="filled"
                        color="brand"
                        icon={<CheckmarkCircleRegular />}
                        data-testid="recommended-badge"
                      >
                        Recommended
                      </Badge>
                    )}
                  </div>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {/* Description row */}
          <tr>
            <td className={styles.metricLabel}>Description</td>
            {comparison.variants.map((variant, idx) => (
              <td
                key={variant.name}
                className={`${styles.td} ${idx === selectedIndex ? styles.tdSelected : ""}`}
                data-testid={`variant-card-${idx}`}
              >
                <Body1>{variant.description}</Body1>
              </td>
            ))}
          </tr>

          {/* Resources row */}
          <tr>
            <td className={styles.metricLabel}>Resources</td>
            {comparison.variants.map((variant, idx) => (
              <td
                key={variant.name}
                className={`${styles.td} ${idx === selectedIndex ? styles.tdSelected : ""}`}
              >
                <Text>{variant.resource_count}</Text>
              </td>
            ))}
          </tr>

          {/* Cost row */}
          <tr>
            <td className={styles.metricLabel}>Est. Cost</td>
            {comparison.variants.map((variant, idx) => (
              <td
                key={variant.name}
                className={`${styles.td} ${idx === selectedIndex ? styles.tdSelected : ""}`}
              >
                <Text>
                  ${variant.estimated_monthly_cost_min.toLocaleString()}–$
                  {variant.estimated_monthly_cost_max.toLocaleString()}/mo
                </Text>
              </td>
            ))}
          </tr>

          {/* Complexity row */}
          <tr>
            <td className={styles.metricLabel}>Complexity</td>
            {comparison.variants.map((variant, idx) => (
              <td
                key={variant.name}
                className={`${styles.td} ${idx === selectedIndex ? styles.tdSelected : ""}`}
              >
                <Badge appearance="tint" color={complexityColor(variant.complexity)}>
                  {variant.complexity}
                </Badge>
              </td>
            ))}
          </tr>

          {/* Compliance rows */}
          {allFrameworks.map((fw) => (
            <tr key={fw}>
              <td className={styles.metricLabel}>{fw}</td>
              {comparison.variants.map((variant, idx) => (
                <td
                  key={variant.name}
                  className={`${styles.td} ${idx === selectedIndex ? styles.tdSelected : ""}`}
                >
                  <Text>
                    {variant.compliance_scores[fw] != null
                      ? `${variant.compliance_scores[fw]}%`
                      : "—"}
                  </Text>
                </td>
              ))}
            </tr>
          ))}

          {/* Action row */}
          <tr>
            <td className={styles.metricLabel}>Action</td>
            {comparison.variants.map((variant, idx) => {
              const isRecommended = idx === comparison.recommended_index;
              return (
                <td
                  key={variant.name}
                  className={`${styles.td} ${idx === selectedIndex ? styles.tdSelected : ""}`}
                >
                  <Button
                    appearance={isRecommended ? "primary" : "secondary"}
                    onClick={() => onSelectVariant?.(variant, idx)}
                    data-testid={`select-variant-${idx}`}
                    aria-label={`Use ${variant.name} architecture`}
                  >
                    Use this architecture
                  </Button>
                </td>
              );
            })}
          </tr>
        </tbody>
      </table>

      {/* Trade-off analysis */}
      {comparison.tradeoff_analysis && (
        <Card className={styles.tradeoffSection} data-testid="tradeoff-analysis">
          <Text className={styles.tradeoffTitle}>📊 Trade-off Analysis</Text>
          <Body1>{comparison.tradeoff_analysis}</Body1>
        </Card>
      )}
    </div>
  );
}
