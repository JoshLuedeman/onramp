import { useState, useEffect, useCallback } from "react";
import {
  Body1,
  Body2,
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
import { api } from "../../services/api";

interface TaggingViolation {
  id: string;
  resource_id: string;
  resource_name: string;
  missing_tags: string[];
  resource_type: string;
}

interface TaggingSummaryData {
  compliance_percentage: number;
  total_resources: number;
  compliant_resources: number;
  non_compliant_resources: number;
  required_tags: string[];
  violations: TaggingViolation[];
  last_updated: string;
}

type ComplianceColor = "success" | "warning" | "danger";

function complianceColor(pct: number): ComplianceColor {
  if (pct >= 90) return "success";
  if (pct >= 70) return "warning";
  return "danger";
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
    flex: "1 1 220px",
    paddingTop: tokens.spacingVerticalL,
    paddingBottom: tokens.spacingVerticalL,
    paddingLeft: tokens.spacingHorizontalL,
    paddingRight: tokens.spacingHorizontalL,
  },
  complianceScore: {
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
  tagList: {
    display: "flex",
    gap: tokens.spacingHorizontalS,
    flexWrap: "wrap",
    marginTop: tokens.spacingVerticalS,
  },
  sectionCard: {
    paddingTop: tokens.spacingVerticalL,
    paddingBottom: tokens.spacingVerticalL,
    paddingLeft: tokens.spacingHorizontalL,
    paddingRight: tokens.spacingHorizontalL,
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
});

interface TaggingPanelProps {
  projectId: string;
}

export default function TaggingPanel({ projectId }: TaggingPanelProps) {
  const styles = useStyles();
  const [summary, setSummary] = useState<TaggingSummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.governance.tagging.getSummary(projectId) as unknown;
      setSummary(data as TaggingSummaryData);
    } catch {
      setError("Failed to load tagging data.");
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
        <Spinner size="medium" label="Loading tagging data..." />
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

  if (!summary) {
    return null;
  }

  return (
    <div className={styles.container}>
      {/* Summary */}
      <div className={styles.summaryRow}>
        <Card className={styles.summaryCard}>
          <CardHeader header={<Subtitle2>Compliance</Subtitle2>} />
          <div className={styles.complianceScore}>
            {summary.compliance_percentage}%
          </div>
          <Badge appearance="filled" color={complianceColor(summary.compliance_percentage)}>
            {summary.compliance_percentage >= 90
              ? "Compliant"
              : summary.compliance_percentage >= 70
                ? "Needs Attention"
                : "Non-Compliant"}
          </Badge>
        </Card>
        <Card className={styles.summaryCard}>
          <CardHeader header={<Subtitle2>Total Resources</Subtitle2>} />
          <div className={styles.statValue}>{summary.total_resources}</div>
        </Card>
        <Card className={styles.summaryCard}>
          <CardHeader header={<Subtitle2>Compliant</Subtitle2>} />
          <div className={styles.statValue}>{summary.compliant_resources}</div>
        </Card>
        <Card className={styles.summaryCard}>
          <CardHeader header={<Subtitle2>Non-Compliant</Subtitle2>} />
          <div className={styles.statValue}>{summary.non_compliant_resources}</div>
        </Card>
      </div>

      {/* Required tags */}
      {summary.required_tags.length > 0 && (
        <Card className={styles.sectionCard}>
          <CardHeader header={<Subtitle2>Required Tags</Subtitle2>} />
          <div className={styles.tagList}>
            {summary.required_tags.map((tag) => (
              <Badge key={tag} appearance="outline" color="informative">
                {tag}
              </Badge>
            ))}
          </div>
        </Card>
      )}

      {/* Violations table */}
      {summary.violations.length > 0 ? (
        <Card className={styles.sectionCard}>
          <CardHeader header={<Subtitle2>Violations</Subtitle2>} />
          <Table aria-label="Tagging violations">
            <TableHeader>
              <TableRow>
                <TableHeaderCell>Resource</TableHeaderCell>
                <TableHeaderCell>Type</TableHeaderCell>
                <TableHeaderCell>Missing Tags</TableHeaderCell>
              </TableRow>
            </TableHeader>
            <TableBody>
              {summary.violations.map((v: TaggingViolation) => (
                <TableRow key={v.id}>
                  <TableCell>
                    <Body2>{v.resource_name}</Body2>
                  </TableCell>
                  <TableCell>
                    <Body2>{v.resource_type}</Body2>
                  </TableCell>
                  <TableCell>
                    <Body2>{v.missing_tags.length} missing</Body2>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      ) : (
        <Body1 className={styles.emptyState}>No violations detected.</Body1>
      )}
    </div>
  );
}
