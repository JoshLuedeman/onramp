import { useEffect, useState } from "react";
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
import { useParams } from "react-router-dom";
import { api } from "../services/api";

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
  const { projectId } = useParams<{ projectId: string }>();
  const [loading, setLoading] = useState(false);
  const [files, setFiles] = useState<BicepFile[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [architecture, setArchitecture] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    if (projectId) {
      api.architecture.getByProject(projectId).then((data) => {
        if (data.architecture) {
          setArchitecture(data.architecture as Record<string, unknown>);
        }
      }).catch(console.error);
    } else {
      const stored = sessionStorage.getItem("onramp_architecture");
      if (stored) setArchitecture(JSON.parse(stored));
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) {
      api.bicep.getByProject(projectId).then((data) => {
        if (data.files && data.files.length > 0) {
          setFiles(data.files.map(f => ({
            name: f.file_path || f.name,
            content: f.content,
            size_bytes: f.size_bytes,
          })));
        }
      }).catch(console.error);
    }
  }, [projectId]);

  const handleGenerate = async () => {
    if (!architecture) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.bicep.generate(architecture, {
        use_ai: true,
        project_id: projectId || "",
      });
      setFiles(data.files || []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!architecture) return;
    try {
      const blob = await api.bicep.download(architecture);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "onramp-landing-zone.bicep";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Download failed");
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
