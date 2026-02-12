import { useEffect, useState } from "react";
import {
  makeStyles,
  Title1,
  Card,
  Body1,
  tokens,
  Badge,
  Button,
} from "@fluentui/react-components";
import { ArrowDownloadRegular } from "@fluentui/react-icons";
import type { Architecture } from "../services/api";
import ArchitectureDiagram from "../components/visualizer/ArchitectureDiagram";

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
});

export default function ArchitecturePage() {
  const styles = useStyles();
  const [architecture, setArchitecture] = useState<Architecture | null>(null);

  useEffect(() => {
    const stored = sessionStorage.getItem("onramp_architecture");
    if (stored) {
      setArchitecture(JSON.parse(stored));
    }
  }, []);

  if (!architecture) {
    return (
      <div className={styles.container}>
        <Title1>No architecture generated yet</Title1>
        <Body1>Complete the questionnaire first to generate your landing zone architecture.</Body1>
      </div>
    );
  }

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
            managementGroups={arch.management_groups as Record<string, any>}
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
            <strong>${arch.estimated_monthly_cost_usd?.toLocaleString() || "N/A"}</strong>/month
          </Body1>
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
        <Button appearance="primary" icon={<ArrowDownloadRegular />} size="large">
          Deploy to Azure
        </Button>
      </div>
    </div>
  );
}
