import { useCallback, useRef, useState } from "react";
import {
  Badge,
  Button,
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogSurface,
  DialogTitle,
  DialogTrigger,
  Divider,
  Field,
  Input,
  Label,
  MessageBar,
  MessageBarBody,
  Select,
  Spinner,
  Tab,
  TabList,
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHeaderCell,
  TableRow,
  Text,
  Textarea,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  ArrowUploadRegular,
  CheckmarkCircleRegular,
  DeleteRegular,
  DocumentRegular,
  EditRegular,
  WarningRegular,
} from "@fluentui/react-icons";
import type {
  WorkloadCreateRequest,
  WorkloadImportResult,
  WorkloadRecord,
} from "../services/api";
import { api } from "../services/api";

const useStyles = makeStyles({
  root: {
    maxWidth: "1100px",
    margin: "0 auto",
    padding: tokens.spacingVerticalXL,
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalL,
  },
  heading: {
    fontSize: tokens.fontSizeBase600,
    fontWeight: tokens.fontWeightSemibold,
  },
  tabContent: {
    paddingTop: tokens.spacingVerticalL,
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalM,
  },
  dropZone: {
    border: `2px dashed ${tokens.colorNeutralStroke1}`,
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
  previewSection: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
  },
  errorList: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXS,
  },
  tableWrapper: {
    overflowX: "auto",
  },
  actionRow: {
    display: "flex",
    gap: tokens.spacingHorizontalM,
    alignItems: "center",
    justifyContent: "space-between",
  },
  formGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: tokens.spacingVerticalM,
  },
  formFullRow: {
    gridColumn: "1 / -1",
  },
  importSummary: {
    display: "flex",
    gap: tokens.spacingHorizontalM,
    alignItems: "center",
  },
});

type TabValue = "import" | "inventory";

const WORKLOAD_TYPES = ["vm", "database", "web-app", "container", "other"];
const SOURCE_PLATFORMS = ["vmware", "hyperv", "physical", "aws", "gcp", "other"];
const CRITICALITY_OPTIONS = ["mission-critical", "business-critical", "standard", "dev-test"];
const MIGRATION_STRATEGIES = ["rehost", "refactor", "rearchitect", "rebuild", "replace", "unknown"];

interface WorkloadsPageProps {
  projectId?: string;
}

function emptyDraft(projectId: string): WorkloadCreateRequest {
  return {
    project_id: projectId,
    name: "",
    type: "other",
    source_platform: "other",
    cpu_cores: null,
    memory_gb: null,
    storage_gb: null,
    os_type: null,
    os_version: null,
    criticality: "standard",
    compliance_requirements: [],
    dependencies: [],
    migration_strategy: "unknown",
    notes: null,
  };
}

export default function WorkloadsPage({ projectId = "dev-project" }: WorkloadsPageProps) {
  const styles = useStyles();
  const [activeTab, setActiveTab] = useState<TabValue>("import");

  // Import tab
  const [dragOver, setDragOver] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<WorkloadImportResult | null>(null);
  const [importLoading, setImportLoading] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Inventory tab
  const [workloads, setWorkloads] = useState<WorkloadRecord[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);

  // Create/edit dialog
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<WorkloadRecord | null>(null);
  const [draft, setDraft] = useState<WorkloadCreateRequest>(emptyDraft(projectId));
  const [saveLoading, setSaveLoading] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Delete dialog
  const [deleteTarget, setDeleteTarget] = useState<WorkloadRecord | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      setImportFile(file);
      setImportResult(null);
      setImportError(null);
    }
  }, []);

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
        fetchWorkloads();
      }
    } catch (err) {
      setImportError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setImportLoading(false);
    }
  };

  const fetchWorkloads = useCallback(async () => {
    setListLoading(true);
    setListError(null);
    try {
      const data = await api.workloads.list(projectId);
      setWorkloads(data.workloads);
    } catch (err) {
      setListError(err instanceof Error ? err.message : "Failed to load workloads");
    } finally {
      setListLoading(false);
    }
  }, [projectId]);

  const handleTabChange = (_: unknown, data: { value: unknown }) => {
    const tab = data.value as TabValue;
    setActiveTab(tab);
    if (tab === "inventory" && workloads.length === 0) {
      fetchWorkloads();
    }
  };

  const openCreate = () => {
    setEditTarget(null);
    setDraft(emptyDraft(projectId));
    setSaveError(null);
    setDialogOpen(true);
  };

  const openEdit = (wl: WorkloadRecord) => {
    setEditTarget(wl);
    setDraft({
      project_id: wl.project_id,
      name: wl.name,
      type: wl.type,
      source_platform: wl.source_platform,
      cpu_cores: wl.cpu_cores,
      memory_gb: wl.memory_gb,
      storage_gb: wl.storage_gb,
      os_type: wl.os_type,
      os_version: wl.os_version,
      criticality: wl.criticality,
      compliance_requirements: wl.compliance_requirements,
      dependencies: wl.dependencies,
      migration_strategy: wl.migration_strategy,
      notes: wl.notes,
    });
    setSaveError(null);
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!draft.name.trim()) {
      setSaveError("Name is required");
      return;
    }
    setSaveLoading(true);
    setSaveError(null);
    try {
      if (editTarget) {
        const updated = await api.workloads.update(editTarget.id, draft);
        setWorkloads((prev) => prev.map((w) => (w.id === editTarget.id ? updated : w)));
      } else {
        const created = await api.workloads.create(draft);
        setWorkloads((prev) => [...prev, created]);
      }
      setDialogOpen(false);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaveLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleteLoading(true);
    try {
      await api.workloads.delete(deleteTarget.id);
      setWorkloads((prev) => prev.filter((w) => w.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch {
      // ignore
    } finally {
      setDeleteLoading(false);
    }
  };

  return (
    <div className={styles.root}>
      <Text className={styles.heading}>Workload Inventory</Text>

      <TabList selectedValue={activeTab} onTabSelect={handleTabChange}>
        <Tab value="import" icon={<ArrowUploadRegular />}>Import</Tab>
        <Tab value="inventory" icon={<DocumentRegular />}>Inventory</Tab>
      </TabList>

      {/* ---- Import Tab ---- */}
      {activeTab === "import" && (
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
            <ArrowUploadRegular style={{ fontSize: 32, color: tokens.colorBrandForeground1 }} />
            <Text weight="semibold">
              {importFile ? importFile.name : "Drop a CSV or JSON file here"}
            </Text>
            <Text size={200} style={{ color: tokens.colorNeutralForeground3 }}>
              or click to browse
            </Text>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.json"
              style={{ display: "none" }}
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
              <div style={{ display: "flex", gap: tokens.spacingHorizontalS }}>
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
                <CheckmarkCircleRegular
                  style={{ fontSize: 20, color: tokens.colorStatusSuccessForeground1 }}
                />
                <Text>
                  Imported{" "}
                  <strong>{importResult.imported_count}</strong>{" "}
                  workload{importResult.imported_count !== 1 ? "s" : ""}
                  {importResult.failed_count > 0 && (
                    <span style={{ color: tokens.colorStatusWarningForeground1 }}>
                      {" "}({importResult.failed_count} failed)
                    </span>
                  )}
                </Text>
              </div>

              {importResult.errors.length > 0 && (
                <div className={styles.errorList}>
                  <Text weight="semibold" style={{ color: tokens.colorStatusWarningForeground1 }}>
                    <WarningRegular /> Row errors:
                  </Text>
                  {importResult.errors.map((err, i) => (
                    <Text key={i} size={200} style={{ color: tokens.colorStatusWarningForeground1 }}>
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
      )}

      {/* ---- Inventory Tab ---- */}
      {activeTab === "inventory" && (
        <div className={styles.tabContent}>
          <div className={styles.actionRow}>
            <Text>
              {workloads.length} workload{workloads.length !== 1 ? "s" : ""} in this project
            </Text>
            <div style={{ display: "flex", gap: tokens.spacingHorizontalS }}>
              <Button appearance="subtle" onClick={fetchWorkloads} disabled={listLoading}>
                {listLoading ? <Spinner size="tiny" /> : "Refresh"}
              </Button>
              <Button appearance="primary" onClick={openCreate}>
                Add Workload
              </Button>
            </div>
          </div>

          {listError && (
            <MessageBar intent="error">
              <MessageBarBody>{listError}</MessageBarBody>
            </MessageBar>
          )}
          {listLoading && <Spinner label="Loading workloads\u2026" />}
          {!listLoading && workloads.length === 0 && (
            <MessageBar intent="info">
              <MessageBarBody>
                No workloads yet. Import a file or add one manually.
              </MessageBarBody>
            </MessageBar>
          )}
          {!listLoading && workloads.length > 0 && (
            <div className={styles.tableWrapper}>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHeaderCell>Name</TableHeaderCell>
                    <TableHeaderCell>Type</TableHeaderCell>
                    <TableHeaderCell>Platform</TableHeaderCell>
                    <TableHeaderCell>CPUs</TableHeaderCell>
                    <TableHeaderCell>RAM (GB)</TableHeaderCell>
                    <TableHeaderCell>OS</TableHeaderCell>
                    <TableHeaderCell>Criticality</TableHeaderCell>
                    <TableHeaderCell>Strategy</TableHeaderCell>
                    <TableHeaderCell>Actions</TableHeaderCell>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {workloads.map((wl) => (
                    <TableRow key={wl.id}>
                      <TableCell>{wl.name}</TableCell>
                      <TableCell>{wl.type}</TableCell>
                      <TableCell>{wl.source_platform}</TableCell>
                      <TableCell>{wl.cpu_cores ?? "\u2014"}</TableCell>
                      <TableCell>{wl.memory_gb ?? "\u2014"}</TableCell>
                      <TableCell>{wl.os_type ?? "\u2014"}</TableCell>
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
                      <TableCell>
                        <div style={{ display: "flex", gap: tokens.spacingHorizontalXS }}>
                          <Button
                            appearance="subtle"
                            size="small"
                            icon={<EditRegular />}
                            onClick={() => openEdit(wl)}
                            aria-label={`Edit ${wl.name}`}
                          />
                          <Button
                            appearance="subtle"
                            size="small"
                            icon={<DeleteRegular />}
                            onClick={() => setDeleteTarget(wl)}
                            aria-label={`Delete ${wl.name}`}
                          />
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      )}

      {/* ---- Create/Edit Dialog ---- */}
      <Dialog open={dialogOpen} onOpenChange={(_, d) => setDialogOpen(d.open)}>
        <DialogSurface>
          <DialogBody>
            <DialogTitle>{editTarget ? "Edit Workload" : "Add Workload"}</DialogTitle>
            <DialogContent>
              <div className={styles.formGrid}>
                <Field label="Name" required className={styles.formFullRow}>
                  <Input
                    value={draft.name}
                    onChange={(_, d) => setDraft((p: WorkloadCreateRequest) => ({ ...p, name: d.value }))}
                    placeholder="e.g. web-server-01"
                  />
                </Field>
                <Field label="Type">
                  <Select
                    value={draft.type ?? "other"}
                    onChange={(_, d) => setDraft((p: WorkloadCreateRequest) => ({ ...p, type: d.value }))}
                  >
                    {WORKLOAD_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </Select>
                </Field>
                <Field label="Source Platform">
                  <Select
                    value={draft.source_platform ?? "other"}
                    onChange={(_, d) => setDraft((p: WorkloadCreateRequest) => ({ ...p, source_platform: d.value }))}
                  >
                    {SOURCE_PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
                  </Select>
                </Field>
                <Field label="CPU Cores">
                  <Input
                    type="number"
                    value={draft.cpu_cores != null ? String(draft.cpu_cores) : ""}
                    onChange={(_, d) =>
                      setDraft((p: WorkloadCreateRequest) => ({ ...p, cpu_cores: d.value ? parseInt(d.value, 10) : null }))
                    }
                    placeholder="e.g. 4"
                  />
                </Field>
                <Field label="Memory (GB)">
                  <Input
                    type="number"
                    value={draft.memory_gb != null ? String(draft.memory_gb) : ""}
                    onChange={(_, d) =>
                      setDraft((p: WorkloadCreateRequest) => ({ ...p, memory_gb: d.value ? parseFloat(d.value) : null }))
                    }
                    placeholder="e.g. 16"
                  />
                </Field>
                <Field label="Storage (GB)">
                  <Input
                    type="number"
                    value={draft.storage_gb != null ? String(draft.storage_gb) : ""}
                    onChange={(_, d) =>
                      setDraft((p: WorkloadCreateRequest) => ({ ...p, storage_gb: d.value ? parseFloat(d.value) : null }))
                    }
                    placeholder="e.g. 500"
                  />
                </Field>
                <Field label="OS Type">
                  <Input
                    value={draft.os_type ?? ""}
                    onChange={(_, d) => setDraft((p: WorkloadCreateRequest) => ({ ...p, os_type: d.value || null }))}
                    placeholder="e.g. Windows"
                  />
                </Field>
                <Field label="OS Version">
                  <Input
                    value={draft.os_version ?? ""}
                    onChange={(_, d) => setDraft((p: WorkloadCreateRequest) => ({ ...p, os_version: d.value || null }))}
                    placeholder="e.g. Server 2022"
                  />
                </Field>
                <Field label="Criticality">
                  <Select
                    value={draft.criticality ?? "standard"}
                    onChange={(_, d) => setDraft((p: WorkloadCreateRequest) => ({ ...p, criticality: d.value }))}
                  >
                    {CRITICALITY_OPTIONS.map((c) => <option key={c} value={c}>{c}</option>)}
                  </Select>
                </Field>
                <Field label="Migration Strategy">
                  <Select
                    value={draft.migration_strategy ?? "unknown"}
                    onChange={(_, d) => setDraft((p: WorkloadCreateRequest) => ({ ...p, migration_strategy: d.value }))}
                  >
                    {MIGRATION_STRATEGIES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </Select>
                </Field>
                <Field
                  label="Compliance Requirements"
                  hint="Comma-separated list of framework IDs"
                  className={styles.formFullRow}
                >
                  <Input
                    value={(draft.compliance_requirements ?? []).join(", ")}
                    onChange={(_, d) =>
                      setDraft((p: WorkloadCreateRequest) => ({
                        ...p,
                        compliance_requirements: d.value
                          ? d.value.split(",").map((s) => s.trim()).filter(Boolean)
                          : [],
                      }))
                    }
                    placeholder="e.g. SOC2, ISO27001"
                  />
                </Field>
                <Field label="Notes" className={styles.formFullRow}>
                  <Textarea
                    value={draft.notes ?? ""}
                    onChange={(_, d) => setDraft((p: WorkloadCreateRequest) => ({ ...p, notes: d.value || null }))}
                    placeholder="Optional notes about this workload"
                    rows={3}
                  />
                </Field>
              </div>
              {saveError && (
                <MessageBar intent="error" style={{ marginTop: tokens.spacingVerticalM }}>
                  <MessageBarBody>{saveError}</MessageBarBody>
                </MessageBar>
              )}
            </DialogContent>
            <DialogActions>
              <DialogTrigger disableButtonEnhancement>
                <Button appearance="secondary">Cancel</Button>
              </DialogTrigger>
              <Button
                appearance="primary"
                onClick={handleSave}
                disabled={saveLoading}
                icon={saveLoading ? <Spinner size="tiny" /> : undefined}
              >
                {saveLoading ? "Saving\u2026" : editTarget ? "Save Changes" : "Create Workload"}
              </Button>
            </DialogActions>
          </DialogBody>
        </DialogSurface>
      </Dialog>

      {/* ---- Delete Confirm Dialog ---- */}
      <Dialog open={!!deleteTarget} onOpenChange={(_, d) => !d.open && setDeleteTarget(null)}>
        <DialogSurface>
          <DialogBody>
            <DialogTitle>Delete Workload</DialogTitle>
            <DialogContent>
              <Text>
                Are you sure you want to delete{" "}
                <strong>{deleteTarget?.name}</strong>? This action cannot be undone.
              </Text>
            </DialogContent>
            <DialogActions>
              <DialogTrigger disableButtonEnhancement>
                <Button appearance="secondary">Cancel</Button>
              </DialogTrigger>
              <Button
                appearance="primary"
                onClick={handleDelete}
                disabled={deleteLoading}
                icon={deleteLoading ? <Spinner size="tiny" /> : undefined}
                style={{ backgroundColor: tokens.colorStatusDangerBackground3 }}
              >
                {deleteLoading ? "Deleting\u2026" : "Delete"}
              </Button>
            </DialogActions>
          </DialogBody>
        </DialogSurface>
      </Dialog>

      <Label style={{ display: "none" }}>Workload import file picker</Label>
    </div>
  );
}
