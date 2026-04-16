import { useState } from "react";
import {
  Card,
  TabList,
  Tab,
  Button,
  Text,
  Badge,
  Spinner,
  MessageBar,
  MessageBarBody,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  ArrowDownloadRegular,
  CheckmarkCircleRegular,
  DismissCircleRegular,
  ShieldCheckmarkRegular,
} from "@fluentui/react-icons";
import type { SelectTabData, SelectTabEvent } from "@fluentui/react-components";

export interface CodeFile {
  name: string;
  content: string;
  size_bytes: number;
}

export interface ValidationIssue {
  line: number | null;
  column?: number | null;
  message: string;
  severity: string;
}

export interface ValidationResult {
  is_valid: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
}

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
  },
  toolbar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
  },
  actions: {
    display: "flex",
    gap: tokens.spacingHorizontalS,
    alignItems: "center",
  },
  codeBlock: {
    backgroundColor: tokens.colorNeutralBackground3,
    padding: tokens.spacingVerticalM,
    borderRadius: tokens.borderRadiusMedium,
    fontFamily: "Consolas, 'Courier New', monospace",
    fontSize: tokens.fontSizeBase200,
    overflow: "auto",
    maxHeight: "400px",
    whiteSpace: "pre",
    lineHeight: tokens.lineHeightBase200,
    tabSize: 2,
  },
  fileInfo: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalXS,
  },
  validationSection: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXS,
  },
  validationItem: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalXS,
    fontSize: tokens.fontSizeBase200,
  },
  emptyState: {
    padding: tokens.spacingVerticalXXL,
    textAlign: "center" as const,
    color: tokens.colorNeutralForeground3,
  },
});

export interface CodePreviewProps {
  files: CodeFile[];
  onDownload?: () => void;
  onValidate?: () => Promise<ValidationResult>;
  downloading?: boolean;
  formatLabel?: string;
}

export default function CodePreview({
  files,
  onDownload,
  onValidate,
  downloading = false,
  formatLabel = "Code",
}: CodePreviewProps) {
  const styles = useStyles();
  const [activeFile, setActiveFile] = useState<string>(
    files.length > 0 ? files[0].name : "",
  );
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] =
    useState<ValidationResult | null>(null);

  const handleTabSelect = (_event: SelectTabEvent, data: SelectTabData) => {
    setActiveFile(data.value as string);
  };

  const handleValidate = async () => {
    if (!onValidate) return;
    setValidating(true);
    setValidationResult(null);
    try {
      const result = await onValidate();
      setValidationResult(result);
    } catch {
      setValidationResult({
        is_valid: false,
        errors: [{ line: null, message: "Validation request failed", severity: "error" }],
        warnings: [],
      });
    } finally {
      setValidating(false);
    }
  };

  const currentFile = files.find((f) => f.name === activeFile);

  if (files.length === 0) {
    return (
      <Card>
        <div className={styles.emptyState}>
          <Text>No files generated yet. Select a format and click Generate.</Text>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className={styles.container}>
        <div className={styles.toolbar}>
          <Text weight="semibold">
            {formatLabel} — {files.length} file{files.length !== 1 ? "s" : ""}
          </Text>
          <div className={styles.actions}>
            {onValidate && (
              <Button
                appearance="subtle"
                icon={
                  validating ? (
                    <Spinner size="tiny" />
                  ) : (
                    <ShieldCheckmarkRegular />
                  )
                }
                onClick={handleValidate}
                disabled={validating}
                size="small"
              >
                Validate
              </Button>
            )}
            {onDownload && (
              <Button
                appearance="primary"
                icon={
                  downloading ? (
                    <Spinner size="tiny" />
                  ) : (
                    <ArrowDownloadRegular />
                  )
                }
                onClick={onDownload}
                disabled={downloading}
                size="small"
              >
                Download
              </Button>
            )}
          </div>
        </div>

        {files.length > 1 && (
          <TabList
            selectedValue={activeFile}
            onTabSelect={handleTabSelect}
            size="small"
            aria-label="Generated files"
          >
            {files.map((file) => (
              <Tab key={file.name} value={file.name}>
                <div className={styles.fileInfo}>
                  {file.name}
                  <Badge appearance="outline" size="small">
                    {(file.size_bytes / 1024).toFixed(1)} KB
                  </Badge>
                </div>
              </Tab>
            ))}
          </TabList>
        )}

        {currentFile && (
          <pre className={styles.codeBlock} data-testid="code-content">
            <code>{currentFile.content}</code>
          </pre>
        )}

        {validationResult && (
          <div className={styles.validationSection}>
            <MessageBar
              intent={validationResult.is_valid ? "success" : "error"}
            >
              <MessageBarBody>
                {validationResult.is_valid
                  ? "Validation passed — no issues found."
                  : `Validation failed — ${validationResult.errors.length} error(s), ${validationResult.warnings.length} warning(s).`}
              </MessageBarBody>
            </MessageBar>
            {validationResult.errors.map((issue, i) => (
              <div key={`err-${i}`} className={styles.validationItem}>
                <DismissCircleRegular
                  color={tokens.colorPaletteRedForeground1}
                />
                <Text>
                  {issue.line != null ? `Line ${issue.line}: ` : ""}
                  {issue.message}
                </Text>
              </div>
            ))}
            {validationResult.warnings.map((issue, i) => (
              <div key={`warn-${i}`} className={styles.validationItem}>
                <CheckmarkCircleRegular
                  color={tokens.colorPaletteYellowForeground1}
                />
                <Text>
                  {issue.line != null ? `Line ${issue.line}: ` : ""}
                  {issue.message}
                </Text>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}
