import { useState } from "react";
import {
  Card,
  Text,
  Button,
  Badge,
  Spinner,
  makeStyles,
  tokens,
  MessageBar,
  MessageBarBody,
  Divider,
} from "@fluentui/react-components";
import {
  CodeRegular,
  ArrowDownloadRegular,
  DocumentRegular,
} from "@fluentui/react-icons";

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
  fileHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    cursor: "pointer",
    padding: "8px 0",
  },
  codeBlock: {
    backgroundColor: tokens.colorNeutralBackground3,
    padding: "12px",
    borderRadius: "4px",
    fontFamily: "monospace",
    fontSize: "12px",
    overflow: "auto",
    maxHeight: "300px",
    whiteSpace: "pre",
  },
});

interface BicepFile {
  name: string;
  content: string;
  size_bytes: number;
}

export default function BicepPage() {
  const styles = useStyles();
  const [loading, setLoading] = useState(false);
  const [files, setFiles] = useState<BicepFile[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const stored = sessionStorage.getItem("onramp_architecture");
  const architecture = stored ? JSON.parse(stored) : null;

  const handleGenerate = async () => {
    if (!architecture) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch("/api/bicep/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ architecture }),
      });
      const data = await resp.json();
      setFiles(data.files || []);
    } catch (e: any) {
      setError(e.message || "Generation failed");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!architecture) return;
    try {
      const resp = await fetch("/api/bicep/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ architecture }),
      });
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "onramp-landing-zone.bicep";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      setError(e.message || "Download failed");
    }
  };

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
        <CodeRegular /> Bicep Templates
      </Text>

      <Card className={styles.card}>
        <Text>
          Generate deployable Bicep Infrastructure as Code from your architecture.
        </Text>
        <div style={{ display: "flex", gap: "8px", marginTop: "12px" }}>
          <Button
            appearance="primary"
            icon={<CodeRegular />}
            onClick={handleGenerate}
            disabled={loading}
          >
            {loading ? <Spinner size="tiny" /> : "Generate Bicep"}
          </Button>
          {files.length > 0 && (
            <Button
              appearance="secondary"
              icon={<ArrowDownloadRegular />}
              onClick={handleDownload}
            >
              Download All
            </Button>
          )}
        </div>
      </Card>

      {files.length > 0 && (
        <Card className={styles.card}>
          <Text weight="semibold">
            Generated Files ({files.length})
          </Text>
          <Divider style={{ margin: "8px 0" }} />
          {files.map((file) => (
            <div key={file.name}>
              <div
                className={styles.fileHeader}
                onClick={() =>
                  setExpanded(expanded === file.name ? null : file.name)
                }
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <DocumentRegular />
                  <Text weight="semibold">{file.name}</Text>
                </div>
                <Badge appearance="outline">
                  {(file.size_bytes / 1024).toFixed(1)} KB
                </Badge>
              </div>
              {expanded === file.name && (
                <div className={styles.codeBlock}>{file.content}</div>
              )}
            </div>
          ))}
        </Card>
      )}

      {error && (
        <MessageBar intent="error">
          <MessageBarBody>{error}</MessageBarBody>
        </MessageBar>
      )}
    </div>
  );
}
