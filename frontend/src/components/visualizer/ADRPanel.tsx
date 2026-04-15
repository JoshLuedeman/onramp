import { useState, useCallback } from "react";
import {
  makeStyles,
  tokens,
  Card,
  Body1,
  Title2,
  Badge,
  Button,
  Spinner,
  Accordion,
  AccordionItem,
  AccordionHeader,
  AccordionPanel,
} from "@fluentui/react-components";
import {
  ArrowDownloadRegular,
  DocumentBulletListRegular,
} from "@fluentui/react-icons";
import type { ADRRecord } from "../../services/api";
import { api } from "../../services/api";

interface ADRPanelProps {
  architecture: Record<string, unknown>;
  answers: Record<string, string | string[]>;
  projectId?: string;
}

const useStyles = makeStyles({
  container: {
    marginTop: "24px",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: "16px",
  },
  title: {
    color: tokens.colorBrandForeground1,
  },
  actions: {
    display: "flex",
    gap: "8px",
  },
  emptyState: {
    textAlign: "center" as const,
    padding: "32px",
  },
  adrHeader: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  adrId: {
    fontFamily: tokens.fontFamilyMonospace,
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
  },
  section: {
    marginBottom: "12px",
  },
  sectionTitle: {
    fontWeight: tokens.fontWeightSemibold,
    marginBottom: "4px",
    color: tokens.colorBrandForeground1,
  },
  errorText: {
    color: tokens.colorPaletteRedForeground1,
    marginTop: "8px",
  },
});

const categoryColors: Record<string, "brand" | "success" | "warning" | "informative" | "important"> = {
  governance: "brand",
  networking: "informative",
  identity: "important",
  compliance: "warning",
};

export default function ADRPanel({ architecture, answers, projectId }: ADRPanelProps) {
  const styles = useStyles();
  const [adrs, setAdrs] = useState<ADRRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.architecture.generateAdrs(architecture, answers, false, projectId);
      setAdrs(result.adrs);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate ADRs");
    } finally {
      setLoading(false);
    }
  }, [architecture, answers, projectId]);

  const handleExport = useCallback(async () => {
    if (adrs.length === 0) return;
    try {
      const result = await api.architecture.exportAdrs(adrs, "combined");
      const blob = new Blob([result.content], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "architecture-decision-records.md";
      link.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to export ADRs");
    }
  }, [adrs]);

  return (
    <Card className={styles.container}>
      <div className={styles.header}>
        <Title2 className={styles.title}>📋 Architecture Decision Records</Title2>
        <div className={styles.actions}>
          {adrs.length > 0 && (
            <Button
              appearance="secondary"
              icon={<ArrowDownloadRegular />}
              onClick={handleExport}
            >
              Export All
            </Button>
          )}
          <Button
            appearance="primary"
            icon={loading ? <Spinner size="tiny" /> : <DocumentBulletListRegular />}
            disabled={loading}
            onClick={handleGenerate}
          >
            {loading ? "Generating..." : adrs.length > 0 ? "Regenerate ADRs" : "Generate ADRs"}
          </Button>
        </div>
      </div>

      {error && <Body1 className={styles.errorText}>{error}</Body1>}

      {adrs.length === 0 && !loading && (
        <div className={styles.emptyState}>
          <Body1>
            No ADRs generated yet. Click &quot;Generate ADRs&quot; to create architecture decision
            records from your landing zone design.
          </Body1>
        </div>
      )}

      {adrs.length > 0 && (
        <Accordion multiple collapsible>
          {adrs.map((adr) => (
            <AccordionItem key={adr.id} value={adr.id}>
              <AccordionHeader>
                <div className={styles.adrHeader}>
                  <span className={styles.adrId}>{adr.id}</span>
                  <span>{adr.title}</span>
                  <Badge
                    appearance="filled"
                    color={categoryColors[adr.category] ?? "brand"}
                    size="small"
                  >
                    {adr.category}
                  </Badge>
                  <Badge appearance="outline" size="small">
                    {adr.status}
                  </Badge>
                </div>
              </AccordionHeader>
              <AccordionPanel>
                <div className={styles.section}>
                  <Body1 className={styles.sectionTitle}>Context</Body1>
                  <Body1>{adr.context}</Body1>
                </div>
                <div className={styles.section}>
                  <Body1 className={styles.sectionTitle}>Decision</Body1>
                  <Body1>{adr.decision}</Body1>
                </div>
                <div className={styles.section}>
                  <Body1 className={styles.sectionTitle}>Consequences</Body1>
                  <Body1>{adr.consequences}</Body1>
                </div>
              </AccordionPanel>
            </AccordionItem>
          ))}
        </Accordion>
      )}
    </Card>
  );
}
