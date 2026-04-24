import { useState, useEffect, useCallback } from "react";
import { useParams } from "react-router-dom";
import {
  Title1,
  Title2,
  Subtitle2,
  Body1,
  Body2,
  Button,
  Card,
  CardHeader,
  Badge,
  Spinner,
  TabList,
  Tab,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import { ArrowClockwiseRegular } from "@fluentui/react-icons";
import { api } from "../services/api";
import type { GovernanceScoreResponse, CategoryScore } from "../services/api";
import { useEventStream } from "../hooks/useEventStream";
import CostPanel from "../components/governance/CostPanel";
import RBACPanel from "../components/governance/RBACPanel";
import TaggingPanel from "../components/governance/TaggingPanel";
import AuditPanel from "../components/governance/AuditPanel";

type BadgeColor = "success" | "warning" | "danger";

function getScoreBadgeColor(score: number): BadgeColor {
  if (score >= 80) return "success";
  if (score >= 60) return "warning";
  return "danger";
}

function getStatusBadgeColor(status: string): BadgeColor {
  switch (status) {
    case "healthy":
      return "success";
    case "warning":
      return "warning";
    case "critical":
      return "danger";
    default:
      return "warning";
  }
}

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXXL,
    padding: tokens.spacingHorizontalXXL,
    maxWidth: "1200px",
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
  headerActions: {
    display: "flex",
    gap: tokens.spacingHorizontalS,
    alignItems: "center",
  },
  scoreSection: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalXL,
    flexWrap: "wrap",
  },
  overallScoreCard: {
    padding: tokens.spacingVerticalXL,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    minWidth: "200px",
  },
  overallScoreValue: {
    fontSize: "48px",
    fontWeight: "bold",
    lineHeight: "1",
    marginTop: tokens.spacingVerticalS,
    marginBottom: tokens.spacingVerticalS,
  },
  categoriesGrid: {
    display: "flex",
    gap: tokens.spacingHorizontalL,
    flexWrap: "wrap",
  },
  categoryCard: {
    flex: "1 1 200px",
    minWidth: "180px",
    padding: tokens.spacingVerticalL,
  },
  categoryHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: tokens.spacingVerticalS,
  },
  categoryScore: {
    fontSize: "28px",
    fontWeight: "bold",
    lineHeight: "1",
    color: tokens.colorBrandForeground1,
    marginTop: tokens.spacingVerticalS,
  },
  categoryFindings: {
    marginTop: tokens.spacingVerticalS,
    color: tokens.colorNeutralForeground3,
  },
  summaryCard: {
    padding: tokens.spacingVerticalL,
  },
  spinnerContainer: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    minHeight: "400px",
  },
  errorContainer: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: tokens.spacingVerticalXXXL,
    gap: tokens.spacingVerticalM,
  },
  lastUpdated: {
    color: tokens.colorNeutralForeground3,
  },
  tabSection: {
    marginTop: tokens.spacingVerticalL,
  },
  tabContent: {
    marginTop: tokens.spacingVerticalL,
  },
});

const CATEGORY_LABELS: Record<string, string> = {
  compliance: "Policy Compliance",
  security: "Security / RBAC",
  cost: "Cost Management",
  drift: "Drift Detection",
  tagging: "Tagging Compliance",
};

export default function GovernancePage() {
  const styles = useStyles();
  const { projectId } = useParams<{ projectId: string }>();
  const resolvedProjectId = projectId ?? "default";

  const [scorecard, setScorecard] = useState<GovernanceScoreResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTab, setSelectedTab] = useState<string>("overview");

  const loadScorecard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.governance.scorecard.getScorecard(resolvedProjectId);
      setScorecard(data);
    } catch {
      setError("Failed to load governance scorecard.");
    } finally {
      setLoading(false);
    }
  }, [resolvedProjectId]);

  useEffect(() => {
    loadScorecard();
  }, [loadScorecard]);

  // Subscribe to real-time governance score updates
  useEventStream(["governance_score_updated"], (event) => {
    if (
      event.event_type === "governance_score_updated" &&
      (event.project_id === resolvedProjectId || event.project_id === null)
    ) {
      const data = event.data as unknown as GovernanceScoreResponse;
      if (data.overall_score !== undefined) {
        setScorecard({
          overall_score: data.overall_score,
          categories: (data.categories ?? []) as CategoryScore[],
          executive_summary: (data.executive_summary as string) ?? "",
          last_updated: new Date().toISOString(),
        });
      }
    }
  });

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const data = await api.governance.scorecard.refreshScore(resolvedProjectId);
      setScorecard(data);
    } catch {
      // Refresh failed silently; existing data remains
    } finally {
      setRefreshing(false);
    }
  }, [resolvedProjectId]);

  if (loading) {
    return (
      <div className={styles.spinnerContainer}>
        <Spinner size="large" label="Loading governance scorecard..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.errorContainer}>
        <Title2>Error</Title2>
        <Body1>{error}</Body1>
        <Button appearance="primary" onClick={loadScorecard}>
          Retry
        </Button>
      </div>
    );
  }

  if (!scorecard) {
    return null;
  }

  const overallColor = getScoreBadgeColor(scorecard.overall_score);

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <Title1>Governance Scorecard</Title1>
        <div className={styles.headerActions}>
          {scorecard.last_updated && (
            <Body2 className={styles.lastUpdated}>
              Last updated: {new Date(scorecard.last_updated).toLocaleString()}
            </Body2>
          )}
          <Button
            icon={<ArrowClockwiseRegular />}
            appearance="primary"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            {refreshing ? "Refreshing..." : "Refresh"}
          </Button>
        </div>
      </div>

      {/* Overall Score */}
      <div className={styles.scoreSection}>
        <Card className={styles.overallScoreCard}>
          <Subtitle2>Overall Governance Score</Subtitle2>
          <div className={styles.overallScoreValue}>
            {Math.round(scorecard.overall_score)}
          </div>
          <Badge
            appearance="filled"
            color={overallColor}
            size="large"
          >
            {overallColor === "success" ? "Healthy" : overallColor === "warning" ? "Needs Attention" : "Critical"}
          </Badge>
        </Card>
      </div>

      {/* Category Breakdown */}
      <Title2>Category Breakdown</Title2>
      <div className={styles.categoriesGrid}>
        {scorecard.categories.map((category: CategoryScore) => (
          <Card key={category.name} className={styles.categoryCard}>
            <CardHeader
              header={
                <Subtitle2>
                  {CATEGORY_LABELS[category.name] ?? category.name}
                </Subtitle2>
              }
            />
            <div className={styles.categoryHeader}>
              <Badge
                appearance="filled"
                color={getStatusBadgeColor(category.status)}
              >
                {category.status}
              </Badge>
            </div>
            <div className={styles.categoryScore}>
              {Math.round(category.score)}
            </div>
            <Body2 className={styles.categoryFindings}>
              {category.finding_count} {category.finding_count === 1 ? "finding" : "findings"}
            </Body2>
          </Card>
        ))}
      </div>

      {/* Executive Summary */}
      <Card className={styles.summaryCard}>
        <CardHeader header={<Title2>Executive Summary</Title2>} />
        <Body1>{scorecard.executive_summary}</Body1>
      </Card>

      {/* Category Detail Tabs */}
      <div className={styles.tabSection}>
        <TabList
          selectedValue={selectedTab}
          onTabSelect={(_, d) => setSelectedTab(d.value as string)}
        >
          <Tab value="overview">Overview</Tab>
          <Tab value="cost">Cost</Tab>
          <Tab value="rbac">RBAC Health</Tab>
          <Tab value="tagging">Tagging</Tab>
          <Tab value="audit">Audit Trail</Tab>
        </TabList>

        <div className={styles.tabContent}>
          {selectedTab === "overview" && (
            <Body1>
              Select a category tab above to see detailed governance information.
            </Body1>
          )}
          {selectedTab === "cost" && (
            <CostPanel projectId={resolvedProjectId} />
          )}
          {selectedTab === "rbac" && (
            <RBACPanel projectId={resolvedProjectId} />
          )}
          {selectedTab === "tagging" && (
            <TaggingPanel projectId={resolvedProjectId} />
          )}
          {selectedTab === "audit" && (
            <AuditPanel projectId={resolvedProjectId} />
          )}
        </div>
      </div>
    </div>
  );
}
