import { useEffect, useState, useCallback } from "react";
import {
  Card,
  Text,
  Button,
  Spinner,
  Badge,
  Divider,
  makeStyles,
  tokens,
  MessageBar,
  MessageBarBody,
} from "@fluentui/react-components";
import { CodeRegular, ArrowSyncRegular } from "@fluentui/react-icons";
import { useParams } from "react-router-dom";
import { api } from "../services/api";
import IaCFormatSelector from "../components/shared/IaCFormatSelector";
import type { IaCFormat } from "../components/shared/IaCFormatSelector";
import CodePreview from "../components/shared/CodePreview";
import type { CodeFile, ValidationResult } from "../components/shared/CodePreview";
import PipelineFormatSelector from "../components/deploy/PipelineFormatSelector";
import type { PipelineConfig } from "../components/deploy/PipelineFormatSelector";

const useStyles = makeStyles({
  container: {
    maxWidth: "1000px",
    margin: "0 auto",
    padding: tokens.spacingVerticalL,
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalM,
  },
  title: {
    fontSize: tokens.fontSizeBase600,
    fontWeight: tokens.fontWeightSemibold,
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
  },
  card: {
    padding: tokens.spacingVerticalL,
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalM,
  },
  sectionTitle: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase400,
  },
  row: {
    display: "flex",
    gap: tokens.spacingHorizontalS,
    alignItems: "center",
  },
  versionGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
    gap: tokens.spacingHorizontalS,
  },
  versionItem: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: tokens.spacingVerticalXS,
  },
});

interface VersionEntry {
  name: string;
  version: string;
  is_stale: boolean;
}

const FORMAT_LABELS: Record<IaCFormat, string> = {
  bicep: "Bicep",
  terraform: "Terraform",
  arm: "ARM Template",
  pulumi_ts: "Pulumi (TypeScript)",
  pulumi_python: "Pulumi (Python)",
};

const FORMAT_API_NAMES: Record<IaCFormat, string> = {
  bicep: "bicep",
  terraform: "terraform",
  arm: "arm",
  pulumi_ts: "pulumi",
  pulumi_python: "pulumi",
};

export default function OutputPage() {
  const styles = useStyles();
  const { projectId } = useParams<{ projectId: string }>();

  const [architecture, setArchitecture] = useState<Record<string, unknown> | null>(null);
  const [iacFormat, setIaCFormat] = useState<IaCFormat>("bicep");
  const [files, setFiles] = useState<CodeFile[]>([]);
  const [generating, setGenerating] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [versionEntries, setVersionEntries] = useState<VersionEntry[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(false);

  const [pipelineConfig, setPipelineConfig] = useState<PipelineConfig>({
    pipelineFormat: "github_actions",
    iacFormat: "bicep",
    serviceConnection: "",
  });
  const [pipelineFiles, setPipelineFiles] = useState<CodeFile[]>([]);
  const [pipelineGenerating, setPipelineGenerating] = useState(false);
  const [pipelineError, setPipelineError] = useState<string | null>(null);

  // Load architecture
  useEffect(() => {
    if (projectId) {
      api.architecture
        .getByProject(projectId)
        .then((data) => {
          if (data.architecture) {
            setArchitecture(data.architecture as Record<string, unknown>);
          }
        })
        .catch(console.error);
    } else {
      const stored = sessionStorage.getItem("onramp_architecture");
      if (stored) setArchitecture(JSON.parse(stored) as Record<string, unknown>);
    }
  }, [projectId]);

  // Load version report
  useEffect(() => {
    setVersionsLoading(true);
    api.versions
      .report()
      .then((data) => {
        const entries: VersionEntry[] = [
          ...data.terraform,
          ...data.pulumi_typescript,
          ...data.pulumi_python,
          ...data.arm,
          ...data.bicep,
        ];
        setVersionEntries(entries);
      })
      .catch(() => {
        // Version info is optional — don't block the page
      })
      .finally(() => setVersionsLoading(false));
  }, []);

  // Clear files when format changes
  useEffect(() => {
    setFiles([]);
    setError(null);
  }, [iacFormat]);

  const handleGenerate = useCallback(async () => {
    if (!architecture) return;
    setGenerating(true);
    setError(null);
    try {
      let result: { files: CodeFile[] };
      switch (iacFormat) {
        case "bicep":
          result = await api.bicep.generate(architecture, {
            use_ai: true,
            project_id: projectId || "",
          });
          break;
        case "terraform":
          result = await api.terraform.generate(architecture, {
            use_ai: true,
            project_id: projectId || "",
          });
          break;
        case "arm":
          result = await api.arm.generate(architecture, {
            use_ai: true,
            project_id: projectId || "",
          });
          break;
        case "pulumi_ts":
          result = await api.pulumi.generate(architecture, {
            language: "typescript",
            use_ai: true,
            project_id: projectId || "",
          });
          break;
        case "pulumi_python":
          result = await api.pulumi.generate(architecture, {
            language: "python",
            use_ai: true,
            project_id: projectId || "",
          });
          break;
      }
      setFiles(
        result.files.map((f) => ({
          name: "file_path" in f ? (f as Record<string, unknown>).file_path as string || f.name : f.name,
          content: f.content,
          size_bytes: f.size_bytes,
        })),
      );
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  }, [architecture, iacFormat, projectId]);

  const handleDownload = useCallback(async () => {
    if (!architecture) return;
    setDownloading(true);
    try {
      let blob: Blob;
      switch (iacFormat) {
        case "bicep":
          blob = await api.bicep.download(architecture);
          break;
        case "terraform":
          blob = await api.terraform.download(architecture);
          break;
        case "arm":
          blob = await api.arm.download(architecture);
          break;
        case "pulumi_ts":
          blob = await api.pulumi.download(architecture, { language: "typescript" });
          break;
        case "pulumi_python":
          blob = await api.pulumi.download(architecture, { language: "python" });
          break;
      }
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `onramp-${iacFormat}.zip`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Download failed");
    } finally {
      setDownloading(false);
    }
  }, [architecture, iacFormat]);

  const handleValidate = useCallback(async (): Promise<ValidationResult> => {
    if (files.length === 0) {
      return { is_valid: false, errors: [{ line: null, message: "No files to validate", severity: "error" }], warnings: [] };
    }
    const formatName = FORMAT_API_NAMES[iacFormat];
    if (files.length === 1) {
      const result = await api.iacValidation.validate(
        files[0].content,
        formatName,
        files[0].name,
      );
      return {
        is_valid: result.is_valid,
        errors: result.errors,
        warnings: result.warnings.map((w) => ({ ...w, severity: "warning" })),
      };
    }
    const bundleResult = await api.iacValidation.validateBundle(
      files.map((f) => ({ code: f.content, file_name: f.name })),
      formatName,
    );
    return {
      is_valid: bundleResult.is_valid,
      errors: bundleResult.bundle_errors,
      warnings: bundleResult.bundle_warnings.map((w) => ({ ...w, severity: "warning" })),
    };
  }, [files, iacFormat]);

  const handlePipelineGenerate = useCallback(async () => {
    if (!architecture) return;
    setPipelineGenerating(true);
    setPipelineError(null);
    try {
      const result = await api.pipelines.generate(
        architecture,
        pipelineConfig.iacFormat,
        {
          pipeline_format: pipelineConfig.pipelineFormat,
          ...(pipelineConfig.pipelineFormat === "azure_devops" &&
          pipelineConfig.serviceConnection
            ? { service_connection: pipelineConfig.serviceConnection }
            : {}),
        },
      );
      setPipelineFiles(
        result.files.map((f) => ({
          name: f.name,
          content: f.content,
          size_bytes: f.size_bytes,
        })),
      );
    } catch (e: unknown) {
      setPipelineError(e instanceof Error ? e.message : "Pipeline generation failed");
    } finally {
      setPipelineGenerating(false);
    }
  }, [architecture, pipelineConfig]);

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
        <CodeRegular /> Infrastructure as Code Output
      </Text>

      {/* IaC Format Selection & Generation */}
      <Card className={styles.card}>
        <Text className={styles.sectionTitle}>Select IaC Format</Text>
        <IaCFormatSelector
          selectedFormat={iacFormat}
          onFormatChange={setIaCFormat}
          disabled={generating}
        />
        <div className={styles.row}>
          <Button
            appearance="primary"
            icon={generating ? <Spinner size="tiny" /> : <CodeRegular />}
            onClick={handleGenerate}
            disabled={generating}
          >
            {generating ? "Generating..." : `Generate ${FORMAT_LABELS[iacFormat]}`}
          </Button>
        </div>
      </Card>

      {/* Code Preview */}
      {files.length > 0 && (
        <CodePreview
          files={files}
          onDownload={handleDownload}
          onValidate={handleValidate}
          downloading={downloading}
          formatLabel={FORMAT_LABELS[iacFormat]}
        />
      )}

      {error && (
        <MessageBar intent="error">
          <MessageBarBody>{error}</MessageBarBody>
        </MessageBar>
      )}

      <Divider />

      {/* Pipeline Generation */}
      <Card className={styles.card}>
        <Text className={styles.sectionTitle}>CI/CD Pipeline Generation</Text>
        <PipelineFormatSelector
          config={pipelineConfig}
          onConfigChange={setPipelineConfig}
          disabled={pipelineGenerating}
        />
        <Button
          appearance="primary"
          icon={pipelineGenerating ? <Spinner size="tiny" /> : <ArrowSyncRegular />}
          onClick={handlePipelineGenerate}
          disabled={pipelineGenerating}
        >
          {pipelineGenerating ? "Generating..." : "Generate Pipeline"}
        </Button>
      </Card>

      {pipelineFiles.length > 0 && (
        <CodePreview
          files={pipelineFiles}
          formatLabel="Pipeline"
        />
      )}

      {pipelineError && (
        <MessageBar intent="error">
          <MessageBarBody>{pipelineError}</MessageBarBody>
        </MessageBar>
      )}

      {/* Version Pinning Report */}
      <Card className={styles.card}>
        <Text className={styles.sectionTitle}>
          <ArrowSyncRegular /> Version Pinning
        </Text>
        {versionsLoading ? (
          <Spinner size="small" label="Loading version info..." />
        ) : versionEntries.length > 0 ? (
          <div className={styles.versionGrid}>
            {versionEntries.slice(0, 12).map((entry) => (
              <div key={`${entry.name}-${entry.version}`} className={styles.versionItem}>
                <Text size={200}>{entry.name}</Text>
                <Badge
                  appearance="outline"
                  color={entry.is_stale ? "danger" : "success"}
                  size="small"
                >
                  {entry.version}
                </Badge>
              </div>
            ))}
          </div>
        ) : (
          <Text size={200}>Version information unavailable.</Text>
        )}
      </Card>
    </div>
  );
}
