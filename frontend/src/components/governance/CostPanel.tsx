import { useState, useEffect, useCallback } from "react";
import {
  Body1,
  Body2,
  Card,
  CardHeader,
  Subtitle2,
  Badge,
  Spinner,
  Title2,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import { api } from "../../services/api";

interface CostSummaryData {
  total_monthly_cost: number;
  currency: string;
  top_services: Array<{ service: string; cost: number }>;
  trend: string;
  change_percentage: number;
  last_updated: string;
}

interface BudgetData {
  budget_amount: number;
  current_spend: number;
  utilization_percentage: number;
  forecast_end_of_month: number;
  currency: string;
  alerts: Array<{ threshold: number; triggered: boolean; message: string }>;
}

/** Format a number with commas and 2 decimal places (locale-independent). */
function formatMoney(value: number): string {
  const parts = value.toFixed(2).split(".");
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return parts.join(".");
}

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalL,
  },
  summaryRow: {
    display: "flex",
    gap: tokens.spacingHorizontalL,
    flexWrap: "wrap",
  },
  summaryCard: {
    flex: "1 1 250px",
    paddingTop: tokens.spacingVerticalL,
    paddingBottom: tokens.spacingVerticalL,
    paddingLeft: tokens.spacingHorizontalL,
    paddingRight: tokens.spacingHorizontalL,
  },
  totalCost: {
    fontSize: tokens.fontSizeHero800,
    fontWeight: tokens.fontWeightBold,
    lineHeight: tokens.lineHeightHero800,
    color: tokens.colorBrandForeground1,
  },
  serviceList: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
    marginTop: tokens.spacingVerticalM,
  },
  serviceRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  budgetBarOuter: {
    width: "100%",
    height: "12px",
    backgroundColor: tokens.colorNeutralBackground3,
    borderRadius: tokens.borderRadiusMedium,
    marginTop: tokens.spacingVerticalS,
    marginBottom: tokens.spacingVerticalS,
    overflow: "hidden",
  },
  budgetBarInner: {
    height: "100%",
    borderRadius: tokens.borderRadiusMedium,
    transitionProperty: "width",
    transitionDuration: "0.3s",
  },
  spinnerContainer: {
    display: "flex",
    justifyContent: "center",
    paddingTop: tokens.spacingVerticalXXL,
    paddingBottom: tokens.spacingVerticalXXL,
  },
  errorText: {
    color: tokens.colorPaletteRedForeground1,
  },
});

interface CostPanelProps {
  projectId: string;
}

export default function CostPanel({ projectId }: CostPanelProps) {
  const styles = useStyles();
  const [summary, setSummary] = useState<CostSummaryData | null>(null);
  const [budget, setBudget] = useState<BudgetData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, budgetData] = await Promise.all([
        api.governance.cost.getSummary(projectId) as Promise<unknown>,
        api.governance.cost.getBudget(projectId) as Promise<unknown>,
      ]);
      setSummary(summaryData as CostSummaryData);
      setBudget(budgetData as BudgetData);
    } catch {
      setError("Failed to load cost data.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <div className={styles.spinnerContainer}>
        <Spinner size="medium" label="Loading cost data..." />
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className={styles.container}>
        <Body1 className={styles.errorText}>{error ?? "No cost data available."}</Body1>
      </div>
    );
  }

  const budgetPct = budget ? Math.min(budget.utilization_percentage, 100) : 0;
  const isOverBudget = budget ? budget.utilization_percentage >= 100 : false;
  const isOverThreshold = budget
    ? budget.alerts.some((a) => a.triggered)
    : false;
  const budgetColor = isOverBudget
    ? tokens.colorPaletteRedBackground3
    : isOverThreshold
      ? tokens.colorPaletteYellowBackground3
      : tokens.colorPaletteGreenBackground3;

  return (
    <div className={styles.container}>
      <div className={styles.summaryRow}>
        {/* Total Cost */}
        <Card className={styles.summaryCard}>
          <CardHeader header={<Subtitle2>Total Monthly Cost</Subtitle2>} />
          <div className={styles.totalCost}>
            {summary.currency}{" "}
            {formatMoney(summary.total_monthly_cost)}
          </div>
          <Body2>
            Trend: {summary.trend} ({summary.change_percentage}%)
          </Body2>
        </Card>

        {/* Budget */}
        {budget && (
          <Card className={styles.summaryCard}>
            <CardHeader header={<Subtitle2>Budget</Subtitle2>} />
            <Body2>
              Budget: {budget.currency} {formatMoney(budget.budget_amount)}
            </Body2>
            <div className={styles.budgetBarOuter}>
              <div
                className={styles.budgetBarInner}
                style={{ width: `${budgetPct}%`, backgroundColor: budgetColor }}
              />
            </div>
            <Badge
              appearance="filled"
              color={
                isOverBudget ? "danger" : isOverThreshold ? "warning" : "success"
              }
            >
              {budgetPct.toFixed(0)}% utilized
            </Badge>
          </Card>
        )}
      </div>

      {/* Cost by service */}
      <Card className={styles.summaryCard}>
        <CardHeader header={<Title2>Top Services</Title2>} />
        <div className={styles.serviceList}>
          {summary.top_services.map((svc) => (
            <div key={svc.service} className={styles.serviceRow}>
              <Body1>{svc.service}</Body1>
              <Body2>
                {summary.currency}{" "}
                {formatMoney(svc.cost)}
              </Body2>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
