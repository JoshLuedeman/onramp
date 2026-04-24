import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Text,
  makeStyles,
  tokens,
  Divider,
  ProgressBar,
} from "@fluentui/react-components";
import {
  ShieldCheckmarkRegular,
  PlayRegular,
  WrenchRegular,
  ErrorCircleRegular,
  WarningRegular,
  InfoRegular,
  CheckmarkCircleRegular,
} from "@fluentui/react-icons";

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "12px",
  },
  scoreCard: {
    padding: "20px",
    display: "flex",
    alignItems: "center",
    gap: "20px",
  },
  scoreCircle: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    width: "80px",
    height: "80px",
    borderRadius: "50%",
    fontWeight: tokens.fontWeightBold,
    fontSize: tokens.fontSizeBase600,
  },
  scoreGreen: {
    backgroundColor: tokens.colorPaletteGreenBackground2,
    color: tokens.colorPaletteGreenForeground1,
  },
  scoreYellow: {
    backgroundColor: tokens.colorPaletteYellowBackground2,
    color: tokens.colorPaletteYellowForeground1,
  },
  scoreRed: {
    backgroundColor: tokens.colorPaletteRedBackground2,
    color: tokens.colorPaletteRedForeground1,
  },
  scoreDetails: {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
    flex: 1,
  },
  findingCard: {
    padding: "16px",
  },
  findingHeader: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    cursor: "pointer",
  },
  findingBody: {
    marginTop: "10px",
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  label: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
    textTransform: "uppercase",
  },
  actions: {
    display: "flex",
    gap: "8px",
    marginTop: "8px",
  },
  emptyState: {
    textAlign: "center",
    padding: "32px",
    color: tokens.colorNeutralForeground3,
  },
  headerTitle: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
  },
});

export interface SecurityFindingData {
  id: string;
  severity: "critical" | "high" | "medium" | "low";
  category: string;
  resource: string;
  finding: string;
  remediation: string;
  auto_fixable: boolean;
}

export interface SecurityAnalysisResultData {
  score: number;
  findings: SecurityFindingData[];
  summary: string;
  analyzed_at: string;
}

interface SecurityFindingsProps {
  result?: SecurityAnalysisResultData | null;
  onRunAnalysis?: () => void;
  onFix?: (findingId: string) => void;
  loading?: boolean;
}

function severityBadge(severity: SecurityFindingData["severity"]) {
  switch (severity) {
    case "critical":
      return (
        <Badge color="danger" appearance="filled" icon={<ErrorCircleRegular />}>
          Critical
        </Badge>
      );
    case "high":
      return (
        <Badge color="warning" appearance="filled" icon={<WarningRegular />}>
          High
        </Badge>
      );
    case "medium":
      return (
        <Badge color="informative" appearance="filled" icon={<InfoRegular />}>
          Medium
        </Badge>
      );
    case "low":
    default:
      return (
        <Badge color="subtle" appearance="filled" icon={<CheckmarkCircleRegular />}>
          Low
        </Badge>
      );
  }
}

function scoreColorClass(
  score: number,
  styles: ReturnType<typeof useStyles>,
): string {
  if (score > 80) return styles.scoreGreen;
  if (score > 60) return styles.scoreYellow;
  return styles.scoreRed;
}

export default function SecurityFindings({
  result,
  onRunAnalysis,
  onFix,
  loading = false,
}: SecurityFindingsProps) {
  const styles = useStyles();
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const toggleExpanded = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.headerTitle}>
          <ShieldCheckmarkRegular fontSize={24} />
          <Text size={500} weight="semibold">
            Security Posture
          </Text>
        </div>
        {onRunAnalysis && (
          <Button
            appearance="primary"
            icon={<PlayRegular />}
            onClick={onRunAnalysis}
            disabled={loading}
          >
            {loading ? "Analyzing..." : "Run Analysis"}
          </Button>
        )}
      </div>

      {loading && <ProgressBar />}

      {!result && !loading && (
        <Card className={styles.emptyState}>
          <Text>No security analysis results yet. Click &quot;Run Analysis&quot; to begin.</Text>
        </Card>
      )}

      {result && (
        <>
          {/* Score card */}
          <Card className={styles.scoreCard}>
            <div
              className={`${styles.scoreCircle} ${scoreColorClass(result.score, styles)}`}
              data-testid="security-score"
            >
              {result.score}
            </div>
            <div className={styles.scoreDetails}>
              <Text size={400} weight="semibold">
                Security Score
              </Text>
              <Text size={300}>{result.summary}</Text>
              <Text size={200}>
                Analyzed at {new Date(result.analyzed_at).toLocaleString()}
              </Text>
            </div>
          </Card>

          <Divider />

          {/* Findings list */}
          {result.findings.length === 0 ? (
            <Card className={styles.emptyState}>
              <Text>No security issues found. Your architecture looks secure!</Text>
            </Card>
          ) : (
            result.findings.map((finding) => {
              const isExpanded = expandedIds.has(finding.id);
              return (
                <Card key={finding.id} className={styles.findingCard}>
                  <div
                    className={styles.findingHeader}
                    onClick={() => toggleExpanded(finding.id)}
                    role="button"
                    tabIndex={0}
                    aria-expanded={isExpanded}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        toggleExpanded(finding.id);
                      }
                    }}

                  >
                    {severityBadge(finding.severity)}
                    <Text weight="semibold">{finding.finding}</Text>
                  </div>

                  {isExpanded && (
                    <div className={styles.findingBody}>
                      <div>
                        <Text className={styles.label}>Category</Text>
                        <Text size={300} block>
                          {finding.category}
                        </Text>
                      </div>
                      <div>
                        <Text className={styles.label}>Resource</Text>
                        <Text size={300} block>
                          {finding.resource}
                        </Text>
                      </div>
                      {finding.remediation && (
                        <div>
                          <Text className={styles.label}>Remediation</Text>
                          <Text size={300} block>
                            {finding.remediation}
                          </Text>
                        </div>
                      )}
                      <div className={styles.actions}>
                        {finding.auto_fixable && onFix && (
                          <Button
                            appearance="primary"
                            icon={<WrenchRegular />}
                            onClick={() => onFix(finding.id)}
                            size="small"
                          >
                            Fix
                          </Button>
                        )}
                      </div>
                    </div>
                  )}
                </Card>
              );
            })
          )}
        </>
      )}
    </div>
  );
}
