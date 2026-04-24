import type React from "react";
import { useRef, useState } from "react";
import {
  Badge,
  Button,
  Divider,
  MessageBar,
  MessageBarBody,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHeaderCell,
  TableRow,
  Text,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  ArrowUploadRegular,
  CheckmarkCircleRegular,
  WarningRegular,
} from "@fluentui/react-icons";
import type { WorkloadImportResult } from "../services/api";
import { api } from "../services/api";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface WorkloadImportTabProps {
  projectId: string;
  onImportSuccess: () => void;
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const useStyles = makeStyles({
  tabContent: {
    paddingTop: tokens.spacingVerticalL,
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalM,
  },
  dropZone: {
    borderTopWidth: "2px",
    borderRightWidth: "2px",
    borderBottomWidth: "2px",
    borderLeftWidth: "2px",
    borderTopStyle: "dashed",
    borderRightStyle: "dashed",
    borderBottomStyle: "dashed",
    borderLeftStyle: "dashed",
    borderTopColor: tokens.colorNeutralStroke1,
    borderRightColor: tokens.colorNeutralStroke1,
    borderBottomColor: tokens.colorNeutralStroke1,
    borderLeftColor: tokens.colorNeutralStroke1,
    borderRadius: tokens.borderRadiusMedium,
    padding: tokens.spacingVerticalXXL,
    textAlign: "center",
    cursor: "pointer",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: tokens.spacingVerticalS,
    ":hover": {
      backgroundColor: tokens.colorNeutralBackground2,
    },
  },
  dropZoneActive: {
    backgroundColor: tokens.colorBrandBackground2,
  },
  actionRow: {
    display: "flex",
    gap: tokens.spacingHorizontalM,
    alignItems: "center",
    justifyContent: "space-between",
  },
  buttonRow: {
    display: "flex",
    gap: tokens.spacingHorizontalS,
  },
  uploadIcon: {
    fontSize: "32px",
    color: tokens.colorBrandForeground1,
  },
  browseHint: {
    color: tokens.colorNeutralForeground3,
  },
  hiddenInput: {
    display: "none",
  },
  previewSection: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
  },
  importSummary: {
    display: "flex",
    gap: tokens.spacingHorizontalM,
    alignItems: "center",
  },
  successIcon: {
    fontSize: "20px",
    color: tokens.colorStatusSuccessForeground1,
  },
  failedCount: {
    color: tokens.colorStatusWarningForeground1,
  },
  warningText: {
    color: tokens.colorStatusWarningForeground1,
  },
  errorList: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXS,
  },
  tableWrapper: {
    overflowX: "auto",
  },
});

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function WorkloadImportTab({
  projectId,
  onImportSuccess,
}: WorkloadImportTabProps) {
  const styles = useStyles();

  const [dragOver, setDragOver] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<WorkloadImportResult | null>(null);
  const [importLoading, setImportLoading] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      setImportFile(file);
      setImportResult(null);
      setImportError(null);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    if (file) {
      setImportFile(file);
      setImportResult(null);
      setImportError(null);
    }
  };

  const handleImport = async () => {
    if (!importFile) return;
    setImportLoading(true);
    setImportError(null);
    try {
      const result = await api.workloads.importFile(importFile, projectId);
      setImportResult(result);
      if (result.imported_count > 0) {
        onImportSuccess();
      }
    } catch (err) {
      setImportError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setImportLoading(false);
    }
  };

  return (
    <div className={styles.tabContent}>
      <Text>Upload a CSV or JSON file to bulk-import workloads into this project.</Text>

      <div
        className={`${styles.dropZone} ${dragOver ? styles.dropZoneActive : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
        aria-label="Drop zone for workload import file"
      >
        <ArrowUploadRegular className={styles.uploadIcon} />
        <Text weight="semibold">
          {importFile ? importFile.name : "Drop a CSV or JSON file here"}
        </Text>
        <Text size={200} className={styles.browseHint}>
          or click to browse
        </Text>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.json"
          className={styles.hiddenInput}
          onChange={handleFileSelect}
          aria-label="File input for workload import"
        />
      </div>

      {importFile && (
        <div className={styles.actionRow}>
          <Text>
            Selected: <strong>{importFile.name}</strong>{" "}
            ({(importFile.size / 1024).toFixed(1)} KB)
          </Text>
          <div className={styles.buttonRow}>
            <Button
              appearance="subtle"
              onClick={() => { setImportFile(null); setImportResult(null); setImportError(null); }}
            >
              Clear
            </Button>
            <Button
              appearance="primary"
              onClick={handleImport}
              disabled={importLoading}
              icon={importLoading ? <Spinner size="tiny" /> : undefined}
            >
              {importLoading ? "Importing\u2026" : "Import"}
            </Button>
          </div>
        </div>
      )}

      {importError && (
        <MessageBar intent="error">
          <MessageBarBody>{importError}</MessageBarBody>
        </MessageBar>
      )}

      {importResult && (
        <div className={styles.previewSection}>
          <div className={styles.importSummary}>
            <CheckmarkCircleRegular className={styles.successIcon} />
            <Text>
              Imported{" "}
              <strong>{importResult.imported_count}</strong>{" "}
              workload{importResult.imported_count !== 1 ? "s" : ""}
              {importResult.failed_count > 0 && (
                <span className={styles.failedCount}>
                  {" "}({importResult.failed_count} failed)
                </span>
              )}
            </Text>
          </div>

          {importResult.errors.length > 0 && (
            <div className={styles.errorList}>
              <Text weight="semibold" className={styles.warningText}>
                <WarningRegular /> Row errors:
              </Text>
              {importResult.errors.map((err, i) => (
                <Text key={i} size={200} className={styles.warningText}>
                  {err}
                </Text>
              ))}
            </div>
          )}

          {importResult.workloads.length > 0 && (
            <>
              <Divider />
              <Text weight="semibold">Preview ({importResult.workloads.length} rows)</Text>
              <div className={styles.tableWrapper}>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHeaderCell>Name</TableHeaderCell>
                      <TableHeaderCell>Type</TableHeaderCell>
                      <TableHeaderCell>Platform</TableHeaderCell>
                      <TableHeaderCell>CPUs</TableHeaderCell>
                      <TableHeaderCell>RAM (GB)</TableHeaderCell>
                      <TableHeaderCell>Criticality</TableHeaderCell>
                      <TableHeaderCell>Strategy</TableHeaderCell>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {importResult.workloads.map((wl) => (
                      <TableRow key={wl.id}>
                        <TableCell>{wl.name}</TableCell>
                        <TableCell>{wl.type}</TableCell>
                        <TableCell>{wl.source_platform}</TableCell>
                        <TableCell>{wl.cpu_cores ?? "\u2014"}</TableCell>
                        <TableCell>{wl.memory_gb ?? "\u2014"}</TableCell>
                        <TableCell>
                          <Badge
                            appearance="tint"
                            color={
                              wl.criticality === "mission-critical"
                                ? "danger"
                                : wl.criticality === "business-critical"
                                  ? "warning"
                                  : "informative"
                            }
                          >
                            {wl.criticality}
                          </Badge>
                        </TableCell>
                        <TableCell>{wl.migration_strategy}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
