import { useCallback, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Button,
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogSurface,
  DialogTitle,
  DialogTrigger,
  Label,
  MessageBar,
  MessageBarBody,
  Spinner,
  Tab,
  TabList,
  Text,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  ArrowUploadRegular,
  DocumentRegular,
  LinkRegular,
  ShareRegular,
} from "@fluentui/react-icons";
import type {
  WorkloadCreateRequest,
  WorkloadRecord,
} from "../services/api";
import { api } from "../services/api";
import WorkloadMapper from "../components/migration/WorkloadMapper";
import DependencyGraph from "../components/migration/DependencyGraph";
import WorkloadImportTab from "./WorkloadImportTab";
import WorkloadInventoryTab from "./WorkloadInventoryTab";
import WorkloadFormDialog from "./WorkloadFormDialog";

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
  deleteButton: {
    backgroundColor: tokens.colorStatusDangerBackground3,
  },
  hiddenLabel: {
    display: "none",
  },
});

type TabValue = "import" | "inventory" | "mapping" | "dependencies";

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

export default function WorkloadsPage({ projectId: propProjectId }: WorkloadsPageProps) {
  const { projectId: paramProjectId } = useParams<{ projectId: string }>();
  const projectId = propProjectId ?? paramProjectId ?? "dev-project";
  const styles = useStyles();
  const [activeTab, setActiveTab] = useState<TabValue>("import");

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
  const [deleteError, setDeleteError] = useState<string | null>(null);

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
    setDeleteError(null);
    try {
      await api.workloads.delete(deleteTarget.id);
      setWorkloads((prev) => prev.filter((w) => w.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Delete failed";
      setDeleteError(message);
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
        <Tab value="mapping" icon={<LinkRegular />}>Mapping</Tab>
        <Tab value="dependencies" icon={<ShareRegular />}>Dependencies</Tab>
      </TabList>

      {/* ---- Import Tab ---- */}
      {activeTab === "import" && (
        <WorkloadImportTab
          projectId={projectId}
          onImportSuccess={fetchWorkloads}
        />
      )}

      {/* ---- Inventory Tab ---- */}
      {activeTab === "inventory" && (
        <WorkloadInventoryTab
          workloads={workloads}
          listLoading={listLoading}
          listError={listError}
          onRefresh={fetchWorkloads}
          onOpenCreate={openCreate}
          onOpenEdit={openEdit}
          onDeleteTarget={setDeleteTarget}
        />
      )}

      {/* ---- Dependencies Tab ---- */}
      {activeTab === "dependencies" && (
        <div className={styles.tabContent}>
          <DependencyGraph projectId={projectId} />
        </div>
      )}

      {/* ---- Create/Edit Dialog ---- */}
      <WorkloadFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        editTarget={editTarget}
        draft={draft}
        onDraftChange={setDraft}
        saveLoading={saveLoading}
        saveError={saveError}
        onSave={handleSave}
      />

      {/* ---- Delete Confirm Dialog ---- */}
      <Dialog open={!!deleteTarget} onOpenChange={(_, d) => { if (!d.open) { setDeleteTarget(null); setDeleteError(null); } }}>
        <DialogSurface>
          <DialogBody>
            <DialogTitle>Delete Workload</DialogTitle>
            <DialogContent>
              <Text>
                Are you sure you want to delete{" "}
                <strong>{deleteTarget?.name}</strong>? This action cannot be undone.
              </Text>
              {deleteError && (
                <MessageBar intent="error">
                  <MessageBarBody>{deleteError}</MessageBarBody>
                </MessageBar>
              )}
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
                className={styles.deleteButton}
              >
                {deleteLoading ? "Deleting\u2026" : "Delete"}
              </Button>
            </DialogActions>
          </DialogBody>
        </DialogSurface>
      </Dialog>

      <Label className={styles.hiddenLabel}>Workload import file picker</Label>

      {/* ---- Mapping Tab ---- */}
      {activeTab === "mapping" && (
        <WorkloadMapper projectId={projectId} />
      )}
    </div>
  );
}

