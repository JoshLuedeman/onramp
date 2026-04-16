import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Title1,
  Title2,
  Body1,
  Body2,
  Card,
  Badge,
  Button,
  Spinner,
  ProgressBar,
  makeStyles,
  tokens,
  Table,
  TableHeader,
  TableHeaderCell,
  TableBody,
  TableRow,
  TableCell,
} from "@fluentui/react-components";
import {
  ArrowClockwiseRegular,
  BuildingRegular,
  FolderRegular,
  ShieldCheckmarkRegular,
  RocketRegular,
  WarningRegular,
} from "@fluentui/react-icons";
import { api } from "../services/api";
import type {
  MSPOverviewResponse,
  MSPTenantOverview,
  MSPComplianceSummaryResponse,
} from "../services/api";

type BadgeColor = "success" | "warning" | "danger" | "informative";

function getStatusBadgeColor(status: string): BadgeColor {
  switch (status) {
    case "active":
      return "success";
    case "warning":
      return "warning";
    case "inactive":
      return "danger";
    default:
      return "informative";
  }
}

function getComplianceBadgeColor(score: number): BadgeColor {
  if (score >= 80) return "success";
  if (score >= 60) return "warning";
  return "danger";
}

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXXL,
    padding: tokens.spacingHorizontalXXL,
    maxWidth: "1400px",
    marginLeft: "auto",
    marginRight: "auto",
    width: "100%",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "wrap",
    gap: tokens.spacingHorizontalM,
  },
  overviewCards: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
    gap: tokens.spacingHorizontalL,
  },
  overviewCard: {
    padding: tokens.spacingVerticalL,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: tokens.spacingVerticalS,
  },
  overviewValue: {
    fontSize: tokens.fontSizeHero800,
    fontWeight: tokens.fontWeightBold,
    lineHeight: tokens.lineHeightHero800,
  },
  overviewLabel: {
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
  },
  tableSection: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalM,
  },
  clickableRow: {
    cursor: "pointer",
    ":hover": {
      backgroundColor: tokens.colorNeutralBackground1Hover,
    },
  },
  progressCell: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
    minWidth: "160px",
  },
  alertSection: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
  },
  alertCard: {
    padding: tokens.spacingVerticalM,
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalM,
    borderLeft: `4px solid ${tokens.colorPaletteRedBorderActive}`,
  },
  emptyState: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: tokens.spacingVerticalXXXL,
    gap: tokens.spacingVerticalM,
    color: tokens.colorNeutralForeground3,
  },
  loadingContainer: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: tokens.spacingVerticalXXXL,
    gap: tokens.spacingVerticalM,
  },
});

export default function MSPDashboardPage() {
  const styles = useStyles();
  const navigate = useNavigate();
  const [overview, setOverview] = useState<MSPOverviewResponse | null>(null);
  const [compliance, setCompliance] =
    useState<MSPComplianceSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [overviewData, complianceData] = await Promise.all([
        api.msp.getOverview(),
        api.msp.getComplianceSummary(),
      ]);
      setOverview(overviewData);
      setCompliance(complianceData);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load MSP dashboard",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleTenantClick = (tenantId: string) => {
    navigate(`/msp/tenants/${tenantId}`);
  };

  const totalActiveDeployments =
    overview?.tenants.reduce((sum, t) => sum + t.active_deployments, 0) ?? 0;

  const violatingTenants =
    compliance?.scores_by_tenant.filter((t) => t.status === "failing") ?? [];

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <Spinner size="large" />
        <Body1>Loading MSP dashboard...</Body1>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.emptyState}>
        <WarningRegular fontSize={48} />
        <Title2>Error loading dashboard</Title2>
        <Body1>{error}</Body1>
        <Button appearance="primary" onClick={fetchData}>
          Retry
        </Button>
      </div>
    );
  }

  if (!overview || overview.total_tenants === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <Title1>MSP Dashboard</Title1>
        </div>
        <div className={styles.emptyState}>
          <BuildingRegular fontSize={48} />
          <Title2>No tenants found</Title2>
          <Body1>
            No managed tenants are configured yet. Add tenants to get started.
          </Body1>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <Title1>MSP Dashboard</Title1>
        <Button
          appearance="subtle"
          icon={<ArrowClockwiseRegular />}
          onClick={fetchData}
        >
          Refresh
        </Button>
      </div>

      {/* Overview Cards */}
      <div className={styles.overviewCards}>
        <Card className={styles.overviewCard}>
          <BuildingRegular fontSize={24} />
          <span className={styles.overviewValue}>
            {overview.total_tenants}
          </span>
          <span className={styles.overviewLabel}>Total Tenants</span>
        </Card>
        <Card className={styles.overviewCard}>
          <FolderRegular fontSize={24} />
          <span className={styles.overviewValue}>
            {overview.total_projects}
          </span>
          <span className={styles.overviewLabel}>Total Projects</span>
        </Card>
        <Card className={styles.overviewCard}>
          <ShieldCheckmarkRegular fontSize={24} />
          <span className={styles.overviewValue}>
            {overview.avg_compliance_score}%
          </span>
          <span className={styles.overviewLabel}>Avg Compliance</span>
        </Card>
        <Card className={styles.overviewCard}>
          <RocketRegular fontSize={24} />
          <span className={styles.overviewValue}>
            {totalActiveDeployments}
          </span>
          <span className={styles.overviewLabel}>Active Deployments</span>
        </Card>
      </div>

      {/* Compliance Alerts */}
      {violatingTenants.length > 0 && (
        <div className={styles.alertSection}>
          <Title2>Compliance Alerts</Title2>
          {violatingTenants.map((tenant) => (
            <Card key={tenant.tenant_id} className={styles.alertCard}>
              <WarningRegular />
              <Body2>
                <strong>{tenant.name}</strong> — compliance score{" "}
                {tenant.score}% (failing)
              </Body2>
              <Badge color="danger" appearance="filled">
                Action Required
              </Badge>
            </Card>
          ))}
        </div>
      )}

      {/* Tenant Table */}
      <div className={styles.tableSection}>
        <Title2>Managed Tenants</Title2>
        <Table aria-label="Managed tenants">
          <TableHeader>
            <TableRow>
              <TableHeaderCell>Name</TableHeaderCell>
              <TableHeaderCell>Status</TableHeaderCell>
              <TableHeaderCell>Compliance Score</TableHeaderCell>
              <TableHeaderCell>Projects</TableHeaderCell>
              <TableHeaderCell>Last Activity</TableHeaderCell>
            </TableRow>
          </TableHeader>
          <TableBody>
            {overview.tenants.map((tenant: MSPTenantOverview) => (
              <TableRow
                key={tenant.tenant_id}
                className={styles.clickableRow}
                onClick={() => handleTenantClick(tenant.tenant_id)}
                aria-label={`View ${tenant.name}`}
              >
                <TableCell>{tenant.name}</TableCell>
                <TableCell>
                  <Badge color={getStatusBadgeColor(tenant.status)}>
                    {tenant.status}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className={styles.progressCell}>
                    <ProgressBar
                      value={tenant.compliance_score / 100}
                      color={
                        getComplianceBadgeColor(tenant.compliance_score) ===
                        "danger"
                          ? "error"
                          : getComplianceBadgeColor(
                                tenant.compliance_score,
                              ) === "warning"
                            ? "warning"
                            : "success"
                      }
                      style={{ flex: 1 }}
                    />
                    <Badge
                      color={getComplianceBadgeColor(tenant.compliance_score)}
                    >
                      {tenant.compliance_score}%
                    </Badge>
                  </div>
                </TableCell>
                <TableCell>{tenant.project_count}</TableCell>
                <TableCell>
                  {tenant.last_activity
                    ? new Date(tenant.last_activity).toLocaleDateString()
                    : "—"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
