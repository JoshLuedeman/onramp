/**
 * ArchitectureCompare — side-by-side comparison of architecture variants.
 *
 * Renders three variant cards (cost-optimised, balanced, enterprise-grade)
 * with resource counts, cost ranges, complexity badges, compliance scores,
 * and a "Use this architecture" action.  The balanced variant is annotated
 * with a "Recommended" badge.  A trade-off analysis paragraph is shown
 * beneath the grid.
 */

import {
  Badge,
  Body1,
  Button,
  Card,
  Spinner,
  Text,
  makeStyles,
  mergeClasses,
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
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
    gap: "16px",
    marginTop: "16px",
  },
  card: {
    padding: "20px",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  recommended: {
    borderTopColor: tokens.colorBrandStroke1,
    borderRightColor: tokens.colorBrandStroke1,
    borderBottomColor: tokens.colorBrandStroke1,
    borderLeftColor: tokens.colorBrandStroke1,
    borderTopWidth: "2px",
    borderRightWidth: "2px",
    borderBottomWidth: "2px",
    borderLeftWidth: "2px",
    borderTopStyle: "solid",
    borderRightStyle: "solid",
    borderBottomStyle: "solid",
    borderLeftStyle: "solid",
  },
  cardHeader: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  variantName: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase400,
  },
  metricRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  metricLabel: {
    color: tokens.colorNeutralForeground3,
  },
  metricValue: {
    fontWeight: tokens.fontWeightSemibold,
  },
  tradeoffSection: {
    marginTop: "24px",
    padding: "16px",
  },
  tradeoffTitle: {
    fontWeight: tokens.fontWeightSemibold,
    marginBottom: "8px",
  },
  loading: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "48px 0",
    gap: "12px",
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
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ArchitectureCompare({
  comparison,
  loading = false,
  onSelectVariant,
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

  return (
    <div className={styles.root} data-testid="architecture-compare">
      <div className={styles.grid}>
        {comparison.variants.map((variant, idx) => {
          const isRecommended = idx === comparison.recommended_index;
          return (
            <Card
              key={variant.name}
              className={mergeClasses(styles.card, isRecommended ? styles.recommended : undefined)}
              data-testid={`variant-card-${idx}`}
            >
              {/* Header */}
              <div className={styles.cardHeader}>
                <Text className={styles.variantName}>{variant.name}</Text>
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

              <Body1>{variant.description}</Body1>

              {/* Metrics */}
              <div className={styles.metricRow}>
                <Text className={styles.metricLabel}>Resources</Text>
                <Text className={styles.metricValue}>{variant.resource_count}</Text>
              </div>

              <div className={styles.metricRow}>
                <Text className={styles.metricLabel}>Est. Cost</Text>
                <Text className={styles.metricValue}>
                  ${variant.estimated_monthly_cost_min.toLocaleString()}–$
                  {variant.estimated_monthly_cost_max.toLocaleString()}/mo
                </Text>
              </div>

              <div className={styles.metricRow}>
                <Text className={styles.metricLabel}>Complexity</Text>
                <Badge appearance="tint" color={complexityColor(variant.complexity)}>
                  {variant.complexity}
                </Badge>
              </div>

              {/* Compliance scores */}
              {Object.keys(variant.compliance_scores).length > 0 && (
                <div>
                  <Text className={styles.metricLabel}>Compliance</Text>
                  <ul className={styles.complianceList}>
                    {Object.entries(variant.compliance_scores).map(([fw, score]) => (
                      <li key={fw}>
                        <Text>
                          {fw}: {score}%
                        </Text>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Action */}
              <Button
                appearance={isRecommended ? "primary" : "secondary"}
                onClick={() => onSelectVariant?.(variant, idx)}
                data-testid={`select-variant-${idx}`}
              >
                Use this architecture
              </Button>
            </Card>
          );
        })}
      </div>

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
