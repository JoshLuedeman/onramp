import {
  Button,
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogSurface,
  DialogTitle,
  DialogTrigger,
  Field,
  Input,
  MessageBar,
  MessageBarBody,
  Select,
  Spinner,
  Textarea,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import type { WorkloadCreateRequest, WorkloadRecord } from "../services/api";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const WORKLOAD_TYPES = ["vm", "database", "web-app", "container", "other"];
const SOURCE_PLATFORMS = ["vmware", "hyperv", "physical", "aws", "gcp", "other"];
const CRITICALITY_OPTIONS = ["mission-critical", "business-critical", "standard", "dev-test"];
const MIGRATION_STRATEGIES = ["rehost", "refactor", "rearchitect", "rebuild", "replace", "unknown"];

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface WorkloadFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editTarget: WorkloadRecord | null;
  draft: WorkloadCreateRequest;
  onDraftChange: (updater: (prev: WorkloadCreateRequest) => WorkloadCreateRequest) => void;
  saveLoading: boolean;
  saveError: string | null;
  onSave: () => void;
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const useStyles = makeStyles({
  formGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: tokens.spacingVerticalM,
  },
  formFullRow: {
    gridColumn: "1 / -1",
  },
  saveErrorBar: {
    marginTop: tokens.spacingVerticalM,
  },
});

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function WorkloadFormDialog({
  open,
  onOpenChange,
  editTarget,
  draft,
  onDraftChange,
  saveLoading,
  saveError,
  onSave,
}: WorkloadFormDialogProps) {
  const styles = useStyles();

  return (
    <Dialog open={open} onOpenChange={(_, d) => onOpenChange(d.open)}>
      <DialogSurface>
        <DialogBody>
          <DialogTitle>{editTarget ? "Edit Workload" : "Add Workload"}</DialogTitle>
          <DialogContent>
            <div className={styles.formGrid}>
              <Field label="Name" required className={styles.formFullRow}>
                <Input
                  value={draft.name}
                  onChange={(_, d) => onDraftChange((p: WorkloadCreateRequest) => ({ ...p, name: d.value }))}
                  placeholder="e.g. web-server-01"
                />
              </Field>
              <Field label="Type">
                <Select
                  value={draft.type ?? "other"}
                  onChange={(_, d) => onDraftChange((p: WorkloadCreateRequest) => ({ ...p, type: d.value }))}
                >
                  {WORKLOAD_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </Select>
              </Field>
              <Field label="Source Platform">
                <Select
                  value={draft.source_platform ?? "other"}
                  onChange={(_, d) => onDraftChange((p: WorkloadCreateRequest) => ({ ...p, source_platform: d.value }))}
                >
                  {SOURCE_PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
                </Select>
              </Field>
              <Field label="CPU Cores">
                <Input
                  type="number"
                  value={draft.cpu_cores != null ? String(draft.cpu_cores) : ""}
                  onChange={(_, d) =>
                    onDraftChange((p: WorkloadCreateRequest) => ({ ...p, cpu_cores: d.value ? parseInt(d.value, 10) : null }))
                  }
                  placeholder="e.g. 4"
                />
              </Field>
              <Field label="Memory (GB)">
                <Input
                  type="number"
                  value={draft.memory_gb != null ? String(draft.memory_gb) : ""}
                  onChange={(_, d) =>
                    onDraftChange((p: WorkloadCreateRequest) => ({ ...p, memory_gb: d.value ? parseFloat(d.value) : null }))
                  }
                  placeholder="e.g. 16"
                />
              </Field>
              <Field label="Storage (GB)">
                <Input
                  type="number"
                  value={draft.storage_gb != null ? String(draft.storage_gb) : ""}
                  onChange={(_, d) =>
                    onDraftChange((p: WorkloadCreateRequest) => ({ ...p, storage_gb: d.value ? parseFloat(d.value) : null }))
                  }
                  placeholder="e.g. 500"
                />
              </Field>
              <Field label="OS Type">
                <Input
                  value={draft.os_type ?? ""}
                  onChange={(_, d) => onDraftChange((p: WorkloadCreateRequest) => ({ ...p, os_type: d.value || null }))}
                  placeholder="e.g. Windows"
                />
              </Field>
              <Field label="OS Version">
                <Input
                  value={draft.os_version ?? ""}
                  onChange={(_, d) => onDraftChange((p: WorkloadCreateRequest) => ({ ...p, os_version: d.value || null }))}
                  placeholder="e.g. Server 2022"
                />
              </Field>
              <Field label="Criticality">
                <Select
                  value={draft.criticality ?? "standard"}
                  onChange={(_, d) => onDraftChange((p: WorkloadCreateRequest) => ({ ...p, criticality: d.value }))}
                >
                  {CRITICALITY_OPTIONS.map((c) => <option key={c} value={c}>{c}</option>)}
                </Select>
              </Field>
              <Field label="Migration Strategy">
                <Select
                  value={draft.migration_strategy ?? "unknown"}
                  onChange={(_, d) => onDraftChange((p: WorkloadCreateRequest) => ({ ...p, migration_strategy: d.value }))}
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
                    onDraftChange((p: WorkloadCreateRequest) => ({
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
                  onChange={(_, d) => onDraftChange((p: WorkloadCreateRequest) => ({ ...p, notes: d.value || null }))}
                  placeholder="Optional notes about this workload"
                  rows={3}
                />
              </Field>
            </div>
            {saveError && (
              <MessageBar intent="error" className={styles.saveErrorBar}>
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
              onClick={onSave}
              disabled={saveLoading}
              icon={saveLoading ? <Spinner size="tiny" /> : undefined}
            >
              {saveLoading ? "Saving\u2026" : editTarget ? "Save Changes" : "Create Workload"}
            </Button>
          </DialogActions>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  );
}
