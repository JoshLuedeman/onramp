import { useState, useEffect, useCallback } from "react";
import {
  Body1,
  Body2,
  Button,
  Card,
  CardHeader,
  Subtitle2,
  Badge,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHeaderCell,
  TableRow,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  ShieldCheckmarkRegular,
  ArrowClockwiseRegular,
} from "@fluentui/react-icons";
import { api } from "../../services/api";

interface RBACSummaryData {
  health_score: number;
  total_assignments: number;
  excessive_permissions: number;
  orphaned_assignments: number;
  status: string;
  last_scan: string;
}

interface RBACFinding {
  id: string;
  severity: string;
  type: string;
  principal: string;
  role: string;
  scope: string;
  recommendation: string;
}

interface RBACResultsData {
  findings: RBACFinding[];
  total_count: number;
}

type BadgeColor = "danger" | "warning" | "informative" | "success";

function severityColor(severity: string): BadgeColor {
  switch (severity.toLowerCase()) {
    case "critical":
    case "high":
      return severity.toLowerCase() === "critical" ? "danger" : "warning";
    case "medium":
      return "informative";
    default:
      return "success";
  }
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
    flex: "1 1 200px",
    paddingTop: tokens.spacingVerticalL,
    paddingBottom: tokens.spacingVerticalL,
    paddingLeft: tokens.spacingHorizontalL,
    paddingRight: tokens.spacingHorizontalL,
  },
  healthScore: {
    fontSize: tokens.fontSizeHero800,
    fontWeight: tokens.fontWeightBold,
    lineHeight: tokens.lineHeightHero800,
    color: tokens.colorBrandForeground1,
  },
  statValue: {
    fontSize: tokens.fontSizeBase500,
    fontWeight: tokens.fontWeightSemibold,
    lineHeight: tokens.lineHeightBase500,
    color: tokens.colorNeutralForeground1,
  },
  scanCard: {
    paddingTop: tokens.spacingVerticalL,
    paddingBottom: tokens.spacingVerticalL,
    paddingLeft: tokens.spacingHorizontalL,
    paddingRight: tokens.spacingHorizontalL,
  },
  headerRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: tokens.spacingVerticalM,
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
  emptyState: {
    paddingTop: tokens.spacingVerticalL,
    paddingBottom: tokens.spacingVerticalL,
    textAlign: "center",
    color: tokens.colorNeutralForeground3,
  },
  lastScan: {
    marginTop: tokens.spacingVerticalS,
    color: tokens.colorNeutralForeground3,
  },
});

interface RBACPanelProps {
  projectId: string;
}

export default function RBACPanel({ projectId }: RBACPanelProps) {
  const styles = useStyles();
  const [summary, setSummary] = useState<RBACSummaryData | null>(null);
  const [results, setResults] = useState<RBACResultsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, resultsData] = await Promise.all([
        api.governance.rbac.getSummary(projectId) as Promise<unknown>,
        api.governance.rbac.getResults(projectId) as Promise<unknown>,
      ]);
      setSummary(summaryData as RBACSummaryData);
      setResults(resultsData as RBACResultsData);
    } catch {
      setError("Failed to load RBAC data.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleScan = useCallback(async () => {
    setScanning(true);
    try {
      await api.governance.rbac.scan(projectId);
      await loadData();
    } catch {
      setError("Scan failed. Please try again.");
    } finally {
      setScanning(false);
    }
  }, [projectId, loadData]);

  if (loading) {
    return (
      <div className={styles.spinnerContainer}>
        <Spinner size="medium" label="Loading RBAC data..." />
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className={styles.container}>
        <Body1 className={styles.errorText}>{error}</Body1>
      </div>
    );
  }

  const findings = results?.findings ?? [];

  return (
    <div className={styles.container}>
      {/* Summary cards */}
      <div className={styles.summaryRow}>
        <Card className={styles.summaryCard}>
          <CardHeader
            header={<Subtitle2>Health Score</Subtitle2>}
            image={<ShieldCheckmarkRegular />}
          />
          <div className={styles.healthScore}>
            {summary?.health_score != null ? Math.round(summary.health_score) : "—"}
          </div>
        </Card>
        <Card className={styles.summaryCard}>
          <CardHeader header={<Subtitle2>Total Assignments</Subtitle2>} />
          <div className={styles.statValue}>{summary?.total_assignments ?? 0}</div>
        </Card>
        <Card className={styles.summaryCard}>
          <CardHeader header={<Subtitle2>Excessive Permissions</Subtitle2>} />
          <div className={styles.statValue}>{summary?.excessive_permissions ?? 0}</div>
        </Card>
        <Card className={styles.summaryCard}>
          <CardHeader header={<Subtitle2>Orphaned Assignments</Subtitle2>} />
          <div className={styles.statValue}>{summary?.orphaned_assignments ?? 0}</div>
        </Card>
      </div>

      {/* Scan actions + findings */}
      <Card className={styles.scanCard}>
        <div className={styles.headerRow}>
          <Subtitle2>RBAC Findings</Subtitle2>
          <Button
            icon={<ArrowClockwiseRegular />}
            appearance="primary"
            onClick={handleScan}
            disabled={scanning}
          >
            {scanning ? "Scanning..." : "Run Scan"}
          </Button>
        </div>

        {findings.length > 0 ? (
          <Table aria-label="RBAC findings">
            <TableHeader>
              <TableRow>
                <TableHeaderCell>Severity</TableHeaderCell>
                <TableHeaderCell>Type</TableHeaderCell>
                <TableHeaderCell>Principal</TableHeaderCell>
                <TableHeaderCell>Role</TableHeaderCell>
                <TableHeaderCell>Recommendation</TableHeaderCell>
              </TableRow>
            </TableHeader>
            <TableBody>
              {findings.map((finding: RBACFinding) => (
                <TableRow key={finding.id}>
                  <TableCell>
                    <Badge appearance="filled" color={severityColor(finding.severity)}>
                      {finding.severity}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Body2>{finding.type}</Body2>
                  </TableCell>
                  <TableCell>
                    <Body2>{finding.principal}</Body2>
                  </TableCell>
                  <TableCell>
                    <Body2>{finding.role}</Body2>
                  </TableCell>
                  <TableCell>
                    <Body2>{finding.recommendation}</Body2>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <Body1 className={styles.emptyState}>
            No findings detected. Run a scan to check RBAC health.
          </Body1>
        )}

        {summary?.last_scan && (
          <Body2 className={styles.lastScan} title={new Date(summary.last_scan).toLocaleString()}>
            Last scan completed
          </Body2>
        )}
      </Card>
    </div>
  );
}
