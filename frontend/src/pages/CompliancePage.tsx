import { useState } from "react";
import {
  Card,
  Text,
  Button,
  Checkbox,
  Badge,
  Spinner,
  Divider,
  makeStyles,
  tokens,
  MessageBar,
  MessageBarBody,
  ProgressBar,
} from "@fluentui/react-components";
import {
  ShieldCheckmarkRegular,
  WarningRegular,
  CheckmarkCircleRegular,
  ArrowDownloadRegular,
} from "@fluentui/react-icons";
import { exportComplianceReport } from "../utils/exportUtils";

const useStyles = makeStyles({
  container: {
    maxWidth: "900px",
    margin: "0 auto",
    padding: "24px",
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  title: {
    fontSize: tokens.fontSizeBase600,
    fontWeight: tokens.fontWeightSemibold,
  },
  card: { padding: "20px" },
  frameworkGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
    gap: "12px",
    marginTop: "12px",
  },
  frameworkCard: {
    padding: "12px",
    cursor: "pointer",
  },
  scoreSection: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    margin: "12px 0",
  },
  scoreValue: {
    fontSize: tokens.fontSizeHero800,
    fontWeight: tokens.fontWeightBold,
  },
  gapItem: {
    padding: "8px 0",
    borderBottom: `1px solid ${tokens.colorNeutralStroke1}`,
  },
});

const FRAMEWORKS = [
  { id: "SOC2", name: "SOC 2", desc: "Service Organization Control 2" },
  { id: "HIPAA", name: "HIPAA", desc: "Health Insurance Portability" },
  { id: "PCI-DSS", name: "PCI-DSS", desc: "Payment Card Industry" },
  { id: "FedRAMP", name: "FedRAMP", desc: "Federal Risk Authorization" },
  { id: "NIST 800-53", name: "NIST 800-53", desc: "Security & Privacy Controls" },
  { id: "ISO 27001", name: "ISO 27001", desc: "Information Security Management" },
];

interface FrameworkResult {
  name: string;
  score: number;
  controls_met: number;
  controls_partial: number;
  controls_gap: number;
  gaps: { control: string; description: string; remediation: string }[];
}

interface ScoringResult {
  overall_score: number;
  frameworks: FrameworkResult[];
}

export default function CompliancePage() {
  const styles = useStyles();
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScoringResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const stored = sessionStorage.getItem("onramp_architecture");
  const architecture = stored ? JSON.parse(stored) : null;

  const toggleFramework = (id: string) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((f) => f !== id) : [...prev, id]
    );
    setResult(null);
  };

  const handleScore = async () => {
    if (!architecture || selected.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch("/api/scoring/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ architecture, frameworks: selected }),
      });
      const data = await resp.json();
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Scoring failed");
    } finally {
      setLoading(false);
    }
  };

  const progressColor = (score: number) =>
    score >= 80 ? "success" : score >= 50 ? "warning" : "error";

  const badgeColor = (score: number) =>
    score >= 80 ? "success" : score >= 50 ? "warning" : "danger";

  if (!architecture) {
    return (
      <div className={styles.container}>
        <MessageBar intent="warning">
          <MessageBarBody>
            No architecture found. Complete the wizard first.
          </MessageBarBody>
        </MessageBar>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <Text className={styles.title}>
        <ShieldCheckmarkRegular /> Compliance Scoring
      </Text>

      <Card className={styles.card}>
        <Text weight="semibold">Select Compliance Frameworks</Text>
        <div className={styles.frameworkGrid}>
          {FRAMEWORKS.map((fw) => (
            <Card
              key={fw.id}
              className={styles.frameworkCard}
              onClick={() => toggleFramework(fw.id)}
              style={{
                border: selected.includes(fw.id)
                  ? `2px solid ${tokens.colorBrandBackground}`
                  : undefined,
              }}
            >
              <Checkbox
                checked={selected.includes(fw.id)}
                onChange={() => toggleFramework(fw.id)}
                label={fw.name}
              />
              <Text size={200}>{fw.desc}</Text>
            </Card>
          ))}
        </div>
        <Button
          appearance="primary"
          onClick={handleScore}
          disabled={selected.length === 0 || loading}
          style={{ marginTop: "16px" }}
        >
          {loading ? <Spinner size="tiny" /> : "Score Architecture"}
        </Button>
      </Card>

      {result && (
        <>
          <Card className={styles.card}>
            <div className={styles.scoreSection}>
              <Text className={styles.scoreValue}>{Math.round(result.overall_score)}%</Text>
              <div style={{ flex: 1 }}>
                <Text weight="semibold">Overall Compliance Score</Text>
                <ProgressBar
                  value={result.overall_score / 100}
                  color={progressColor(result.overall_score) as "success" | "warning" | "error"}
                  style={{ marginTop: "4px" }}
                />
              </div>
            </div>
          </Card>

          {result.frameworks.map((fw) => (
            <Card key={fw.name} className={styles.card}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <Text weight="semibold">{fw.name}</Text>
                <Badge
                  color={badgeColor(fw.score) as "success" | "warning" | "danger"}
                  size="large"
                >
                  {Math.round(fw.score)}%
                </Badge>
              </div>
              <Text size={200}>
                {fw.controls_met}/{fw.controls_met + fw.controls_partial + fw.controls_gap} controls satisfied
              </Text>
              <ProgressBar
                value={fw.score / 100}
                color={progressColor(fw.score) as "success" | "warning" | "error"}
                style={{ margin: "8px 0" }}
              />

              {fw.gaps && fw.gaps.length > 0 && (
                <>
                  <Divider style={{ margin: "8px 0" }} />
                  <Text weight="semibold" size={300}>
                    <WarningRegular /> Gaps ({fw.gaps.length})
                  </Text>
                  {fw.gaps.map((gap, i) => (
                    <div key={i} className={styles.gapItem}>
                      <Text weight="semibold">{gap.control}</Text>
                      <br />
                      <Text size={200}>{gap.description}</Text>
                      {gap.remediation && (
                        <>
                          <br />
                          <Text size={200} style={{ color: tokens.colorBrandForeground1 }}>
                            <CheckmarkCircleRegular /> {gap.remediation}
                          </Text>
                        </>
                      )}
                    </div>
                  ))}
                </>
              )}
            </Card>
          ))}

          <Button
            appearance="secondary"
            icon={<ArrowDownloadRegular />}
            onClick={() => exportComplianceReport(result as unknown as Record<string, unknown>)}
          >
            Export Report
          </Button>
        </>
      )}

      {error && (
        <MessageBar intent="error">
          <MessageBarBody>{error}</MessageBarBody>
        </MessageBar>
      )}
    </div>
  );
}
