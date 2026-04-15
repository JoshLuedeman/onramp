import { useEffect, useState } from "react";
import {
  Text,
  Spinner,
  MessageBar,
  MessageBarBody,
  Button,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import { ArrowDownloadRegular } from "@fluentui/react-icons";
import { useParams } from "react-router-dom";
import { api } from "../services/api";
import type { GapAnalysisResponse, BrownfieldContextResponse } from "../services/api";
import GapSummaryBar from "../components/gap/GapSummaryBar";
import GapFindingCard from "../components/gap/GapFindingCard";
import GapComparison from "../components/gap/GapComparison";
import { exportGapAnalysis } from "../utils/exportUtils";

const useStyles = makeStyles({
  container: {
    maxWidth: "1100px",
    margin: "0 auto",
    padding: "24px",
    display: "flex",
    flexDirection: "column",
    gap: "24px",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  },
  title: {
    fontSize: tokens.fontSizeBase600,
    fontWeight: tokens.fontWeightSemibold,
  },
  sectionTitle: {
    fontSize: tokens.fontSizeBase500,
    fontWeight: tokens.fontWeightSemibold,
    marginBottom: "8px",
  },
  findings: {
    display: "flex",
    flexDirection: "column",
    gap: "0",
  },
  emptyState: {
    padding: "32px",
    textAlign: "center",
    color: tokens.colorNeutralForeground3,
  },
});

export default function GapAnalysisPage() {
  const styles = useStyles();
  const { scanId } = useParams<{ scanId: string }>();
  const [gapResult, setGapResult] = useState<GapAnalysisResponse | null>(null);
  const [brownfieldContext, setBrownfieldContext] = useState<BrownfieldContextResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!scanId) return;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [gapData, contextData] = await Promise.all([
          api.discovery.analyzeScanGaps(scanId!),
          api.discovery.getBrownfieldContext(scanId!),
        ]);
        setGapResult(gapData);
        setBrownfieldContext(contextData);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load gap analysis");
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [scanId]);

  if (!scanId) {
    return (
      <div className={styles.container}>
        <MessageBar intent="warning">
          <MessageBarBody>No scan ID provided. Navigate from a scan result.</MessageBarBody>
        </MessageBar>
      </div>
    );
  }

  if (loading) {
    return (
      <div className={styles.container}>
        <Spinner label="Analyzing gaps..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <MessageBar intent="error">
          <MessageBarBody>{error}</MessageBarBody>
        </MessageBar>
      </div>
    );
  }

  if (!gapResult || !brownfieldContext) {
    return null;
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Text className={styles.title}>Gap Analysis</Text>
        <Button
          appearance="secondary"
          icon={<ArrowDownloadRegular />}
          onClick={() => exportGapAnalysis(gapResult)}
        >
          Export Report
        </Button>
      </div>

      <GapSummaryBar result={gapResult} />

      <GapComparison gapResult={gapResult} brownfieldContext={brownfieldContext} />

      <div>
        <Text className={styles.sectionTitle}>
          Findings ({gapResult.total_findings})
        </Text>
        {gapResult.findings.length === 0 ? (
          <Text className={styles.emptyState}>
            No findings. Your environment looks good!
          </Text>
        ) : (
          <div className={styles.findings}>
            {gapResult.findings.map((finding) => (
              <GapFindingCard key={finding.id} finding={finding} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
