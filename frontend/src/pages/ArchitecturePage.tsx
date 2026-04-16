import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  makeStyles,
  Title1,
  Card,
  Body1,
  tokens,
  Badge,
  Button,
  Spinner,
  Table,
  TableHeader,
  TableRow,
  TableHeaderCell,
  TableBody,
  TableCell,
} from "@fluentui/react-components";
import { ArrowDownloadRegular, DocumentRegular, CalculatorRegular } from "@fluentui/react-icons";
import type { Architecture, ComparisonResult, CostEstimation } from "../services/api";
import { api } from "../services/api";
import ArchitectureDiagram from "../components/visualizer/ArchitectureDiagram";
import ArchitectureChat from "../components/visualizer/ArchitectureChat";
import ArchitectureCompare from "../components/visualizer/ArchitectureCompare";
import ADRPanel from "../components/visualizer/ADRPanel";
import { exportArchitectureJson, exportDesignDocument } from "../utils/exportUtils";

const useStyles = makeStyles({
  container: {
    padding: "48px 24px",
    maxWidth: "1200px",
    margin: "0 auto",
  },
  title: {
    marginBottom: "24px",
    color: tokens.colorBrandForeground1,
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
    gap: "16px",
    marginTop: "24px",
  },
  card: {
    padding: "20px",
  },
  cardTitle: {
    fontWeight: tokens.fontWeightSemibold,
    marginBottom: "8px",
  },
  actions: {
    display: "flex",
    gap: "12px",
    marginTop: "24px",
  },
  subscriptionList: {
    listStyle: "none",
    padding: 0,
    margin: 0,
  },
  subscriptionItem: {
    padding: "4px 0",
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
  },
  costBreakdown: {
    marginTop: "12px",
  },
  tipsList: {
    margin: "8px 0 0 0",
    paddingLeft: "20px",
  },
});

export default function ArchitecturePage() {
  const styles = useStyles();
  const navigate = useNavigate();
  const { projectId } = useParams<{ projectId: string }>();
  const [architecture, setArchitecture] = useState<Architecture | null>(null);
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [costEstimation, setCostEstimation] = useState<CostEstimation | null>(null);
  const [costLoading, setCostLoading] = useState(false);
  const [costError, setCostError] = useState<string | null>(null);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);

  useEffect(() => {
    // Load architecture: from API for project-scoped, from sessionStorage for legacy
    if (projectId) {
      api.architecture.getByProject(projectId).then((data) => {
        if (data.architecture) {
          setArchitecture(data.architecture);
        }
      }).catch(console.error);
      // Load saved questionnaire answers for project-scoped flows
      api.questionnaire.loadState(projectId).then((data) => {
        if (data.answers && Object.keys(data.answers).length > 0) {
          setAnswers(data.answers);
        }
      }).catch(console.error);
    } else {
      const stored = sessionStorage.getItem("onramp_architecture");
      if (stored) {
        setArchitecture(JSON.parse(stored));
      }
      // Load answers saved by the wizard during generation
      const storedAnswers = sessionStorage.getItem("onramp_answers");
      if (storedAnswers) {
        setAnswers(JSON.parse(storedAnswers));
      }
    }
  }, [projectId]);

  if (!architecture) {
    return (
      <div className={styles.container}>
        <Title1>No architecture generated yet</Title1>
        <Body1>Complete the questionnaire first to generate your landing zone architecture.</Body1>
      </div>
    );
  }

  const handleEstimateCosts = async () => {
    if (!architecture) return;
    setCostLoading(true);
    setCostError(null);
    try {
      const result = await api.architecture.estimateCosts(architecture as Record<string, unknown>);
      setCostEstimation(result);
    } catch (e) {
      setCostError(e instanceof Error ? e.message : "Failed to estimate costs");
    } finally {
      setCostLoading(false);
    }
  };

  const handleCompare = async () => {
    setCompareLoading(true);
    try {
      const result = await api.architecture.compare(
        answers as Record<string, string>,
      );
      setComparison(result);
    } catch {
      // Silently handle — comparison is optional
    } finally {
      setCompareLoading(false);
    }
  };

  const arch = architecture as Architecture & {
    identity?: Record<string, unknown>;
    security?: Record<string, unknown>;
    governance?: Record<string, unknown>;
    management?: Record<string, unknown>;
    recommendations?: string[];
    estimated_monthly_cost_usd?: number;
  };

  return (
    <div className={styles.container}>
      <Title1 className={styles.title}>Your Landing Zone Architecture</Title1>
      <Badge appearance="filled" color="brand" size="large">
        {arch.organization_size} organization
      </Badge>

      {arch.management_groups && (
        <Card style={{ marginTop: "24px", padding: "16px" }}>
          <Body1 className={styles.cardTitle}>🏗️ Management Group Hierarchy</Body1>
          <ArchitectureDiagram
            managementGroups={arch.management_groups as Record<string, Record<string, unknown>>}
            subscriptions={arch.subscriptions}
          />
        </Card>
      )}

      <div className={styles.grid}>
        <Card className={styles.card}>
          <Body1 className={styles.cardTitle}>📂 Subscriptions</Body1>
          <ul className={styles.subscriptionList}>
            {arch.subscriptions?.map((sub, i) => (
              <li key={i} className={styles.subscriptionItem}>
                <strong>{sub.name}</strong> — {sub.purpose}
              </li>
            ))}
          </ul>
        </Card>

        <Card className={styles.card}>
          <Body1 className={styles.cardTitle}>🌐 Network Topology</Body1>
          <Body1>
            Type: <strong>{String((arch.network_topology as Record<string, unknown>)?.type || "hub-spoke")}</strong>
          </Body1>
          <Body1>
            Region: <strong>{String((arch.network_topology as Record<string, unknown>)?.primary_region || "eastus2")}</strong>
          </Body1>
        </Card>

        <Card className={styles.card}>
          <Body1 className={styles.cardTitle}>🔑 Identity</Body1>
          <Body1>Provider: <strong>{String(arch.identity?.provider || "Entra ID")}</strong></Body1>
          <Body1>PIM: <strong>{String(arch.identity?.pim_enabled || false)}</strong></Body1>
          <Body1>MFA: <strong>{String(arch.identity?.mfa_policy || "all_users")}</strong></Body1>
        </Card>

        <Card className={styles.card}>
          <Body1 className={styles.cardTitle}>🛡️ Security</Body1>
          <Body1>Defender: <strong>{String(arch.security?.defender_for_cloud ?? true)}</strong></Body1>
          <Body1>Sentinel: <strong>{String(arch.security?.sentinel ?? false)}</strong></Body1>
          <Body1>Firewall: <strong>{String(arch.security?.azure_firewall ?? true)}</strong></Body1>
        </Card>

        <Card className={styles.card}>
          <Body1 className={styles.cardTitle}>📋 Governance</Body1>
          <Body1>Naming: <strong>{String((arch.governance as Record<string, unknown>)?.naming_convention || "CAF")}</strong></Body1>
        </Card>

        <Card className={styles.card}>
          <Body1 className={styles.cardTitle}>💰 Estimated Cost</Body1>
          <Body1>
            <strong>
              ${costEstimation
                ? costEstimation.estimated_monthly_total_usd.toLocaleString()
                : arch.estimated_monthly_cost_usd?.toLocaleString() || "N/A"}
            </strong>/month
          </Body1>
          {costEstimation && (
            <>
              <Badge
                appearance="filled"
                color={costEstimation.confidence === "high" ? "success" : costEstimation.confidence === "medium" ? "warning" : "danger"}
                style={{ marginTop: "8px" }}
              >
                {costEstimation.confidence} confidence
              </Badge>
              <div className={styles.costBreakdown}>
                <Table size="small">
                  <TableHeader>
                    <TableRow>
                      <TableHeaderCell>Category</TableHeaderCell>
                      <TableHeaderCell>Service</TableHeaderCell>
                      <TableHeaderCell>Monthly Cost</TableHeaderCell>
                      <TableHeaderCell>Notes</TableHeaderCell>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {costEstimation.breakdown.map((item, i) => (
                      <TableRow key={i}>
                        <TableCell>{item.category}</TableCell>
                        <TableCell>{item.service}</TableCell>
                        <TableCell>${item.estimated_monthly_usd.toLocaleString()}</TableCell>
                        <TableCell>{item.notes}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              {costEstimation.cost_optimization_tips.length > 0 && (
                <div style={{ marginTop: "12px" }}>
                  <Body1 className={styles.cardTitle}>💡 Cost Optimization Tips</Body1>
                  <ul className={styles.tipsList}>
                    {costEstimation.cost_optimization_tips.map((tip, i) => (
                      <li key={i}><Body1>{tip}</Body1></li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
          {costError && <Body1 style={{ color: tokens.colorPaletteRedForeground1, marginTop: "8px" }}>{costError}</Body1>}
          <Button
            appearance="subtle"
            icon={costLoading ? <Spinner size="tiny" /> : <CalculatorRegular />}
            disabled={costLoading}
            onClick={handleEstimateCosts}
            style={{ marginTop: "8px" }}
          >
            {costLoading ? "Estimating..." : costEstimation ? "Re-estimate Costs" : "Estimate Costs"}
          </Button>
        </Card>
      </div>

      {arch.recommendations && arch.recommendations.length > 0 && (
        <Card className={styles.card} style={{ marginTop: "24px" }}>
          <Body1 className={styles.cardTitle}>💡 Recommendations</Body1>
          <ul>
            {arch.recommendations.map((rec, i) => (
              <li key={i}>{rec}</li>
            ))}
          </ul>
        </Card>
      )}

      <div className={styles.actions}>
        <Button
          appearance="primary"
          icon={<ArrowDownloadRegular />}
          size="large"
          onClick={() => navigate(projectId ? `/projects/${projectId}/deploy` : "/deploy")}
        >
          Deploy to Azure
        </Button>
        <Button
          appearance="secondary"
          icon={<DocumentRegular />}
          size="large"
          onClick={() => navigate(projectId ? `/projects/${projectId}/bicep` : "/bicep")}
        >
          View Bicep Templates
        </Button>
        <Button
          appearance="secondary"
          size="large"
          onClick={() => navigate(projectId ? `/projects/${projectId}/compliance` : "/compliance")}
        >
          Score Compliance
        </Button>
        <Button
          appearance="secondary"
          size="large"
          onClick={handleCompare}
          disabled={compareLoading}
        >
          {compareLoading ? "Comparing…" : "Compare Architectures"}
        </Button>
        <Button
          appearance="secondary"
          icon={<ArrowDownloadRegular />}
          size="large"
          onClick={() => exportArchitectureJson(architecture as Record<string, unknown>)}
        >
          Export JSON
        </Button>
        <Button
          appearance="secondary"
          icon={<ArrowDownloadRegular />}
          size="large"
          onClick={() => exportDesignDocument(architecture as Record<string, unknown>)}
        >
          Export Design Document
        </Button>
      </div>

      {(comparison || compareLoading) && (
        <ArchitectureCompare
          comparison={comparison}
          loading={compareLoading}
          onSelectVariant={(variant) => {
            setArchitecture(variant.architecture as Architecture);
            sessionStorage.setItem(
              "onramp_architecture",
              JSON.stringify(variant.architecture),
            );
            setComparison(null);
          }}
        />
      )}

      <ArchitectureChat
        architecture={architecture}
        onArchitectureUpdate={(updated) => {
          setArchitecture(updated);
          sessionStorage.setItem("onramp_architecture", JSON.stringify(updated));
        }}
      />

      <ADRPanel
        architecture={architecture as Record<string, unknown>}
        answers={answers}
        projectId={projectId}
      />
    </div>
  );
}
