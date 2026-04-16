import { useState, useCallback } from "react";
import {
  Badge,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogSurface,
  DialogTitle,
  DialogTrigger,
  Dropdown,
  Option,
  Table,
  TableBody,
  TableCell,
  TableCellLayout,
  TableHeader,
  TableHeaderCell,
  TableRow,
  Text,
  Textarea,
  Toolbar,
  ToolbarButton,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  CheckmarkRegular,
  ArrowUndoRegular,
  EyeOffRegular,
  ErrorCircleRegular,
  WarningRegular,
  InfoRegular,
  CheckmarkCircleRegular,
} from "@fluentui/react-icons";
import type { DriftFinding } from "../../services/api";
import { api } from "../../services/api";

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  toolbar: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "8px 0",
  },
  selectionCount: {
    marginLeft: "auto",
    color: tokens.colorNeutralForeground3,
  },
  actions: {
    display: "flex",
    gap: "4px",
  },
  truncated: {
    maxWidth: "200px",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  resolved: {
    opacity: 0.6,
  },
  dialogField: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
    marginBottom: "12px",
  },
  label: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase200,
  },
});

function severityBadge(severity: DriftFinding["severity"]) {
  switch (severity) {
    case "critical":
      return (
        <Badge color="danger" appearance="filled" icon={<ErrorCircleRegular />}>
          Critical
        </Badge>
      );
    case "high":
      return (
        <Badge color="warning" appearance="filled" icon={<WarningRegular />}>
          High
        </Badge>
      );
    case "medium":
      return (
        <Badge color="informative" appearance="filled" icon={<InfoRegular />}>
          Medium
        </Badge>
      );
    case "low":
    default:
      return (
        <Badge color="subtle" appearance="filled" icon={<CheckmarkCircleRegular />}>
          Low
        </Badge>
      );
  }
}

function statusLabel(finding: DriftFinding): string {
  if (finding.resolved_at) return `Resolved (${finding.resolution_type ?? "unknown"})`;
  return "Active";
}

function resourceName(resourceId: string): string {
  const parts = resourceId.split("/");
  return parts[parts.length - 1] || resourceId;
}

export interface DriftFindingsProps {
  findings: DriftFinding[];
  onActionComplete?: () => void;
}

const EXPIRATION_OPTIONS = [
  { value: "30", label: "30 days" },
  { value: "60", label: "60 days" },
  { value: "90", label: "90 days" },
  { value: "permanent", label: "Permanent" },
];

export default function DriftFindings({ findings, onActionComplete }: DriftFindingsProps) {
  const styles = useStyles();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [suppressDialogOpen, setSuppressDialogOpen] = useState(false);
  const [suppressTarget, setSuppressTarget] = useState<string | string[] | null>(null);
  const [justification, setJustification] = useState("");
  const [expirationDays, setExpirationDays] = useState<string>("30");
  const [loading, setLoading] = useState(false);

  const allSelected = findings.length > 0 && selected.size === findings.length;

  const toggleSelect = useCallback(
    (id: string) => {
      setSelected((prev) => {
        const next = new Set(prev);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        return next;
      });
    },
    [],
  );

  const toggleAll = useCallback(() => {
    if (allSelected) {
      setSelected(new Set());
    } else {
      setSelected(new Set(findings.map((f) => f.id)));
    }
  }, [allSelected, findings]);

  const handleAction = useCallback(
    async (findingId: string, action: "accept" | "revert") => {
      setLoading(true);
      try {
        await api.governance.drift.remediate({ finding_id: findingId, action });
        onActionComplete?.();
      } finally {
        setLoading(false);
      }
    },
    [onActionComplete],
  );

  const handleBatchAction = useCallback(
    async (action: "accept" | "revert") => {
      if (selected.size === 0) return;
      setLoading(true);
      try {
        await api.governance.drift.remediateBatch({
          finding_ids: Array.from(selected),
          action,
        });
        setSelected(new Set());
        onActionComplete?.();
      } finally {
        setLoading(false);
      }
    },
    [selected, onActionComplete],
  );

  const openSuppressDialog = useCallback(
    (target: string | string[]) => {
      setSuppressTarget(target);
      setJustification("");
      setExpirationDays("30");
      setSuppressDialogOpen(true);
    },
    [],
  );

  const handleSuppress = useCallback(async () => {
    if (!suppressTarget) return;
    setLoading(true);
    try {
      const expDays = expirationDays === "permanent" ? undefined : parseInt(expirationDays, 10);
      if (Array.isArray(suppressTarget)) {
        await api.governance.drift.remediateBatch({
          finding_ids: suppressTarget,
          action: "suppress",
          justification: justification || undefined,
          expiration_days: expDays,
        });
        setSelected(new Set());
      } else {
        await api.governance.drift.remediate({
          finding_id: suppressTarget,
          action: "suppress",
          justification: justification || undefined,
          expiration_days: expDays,
        });
      }
      setSuppressDialogOpen(false);
      onActionComplete?.();
    } finally {
      setLoading(false);
    }
  }, [suppressTarget, justification, expirationDays, onActionComplete]);

  return (
    <div className={styles.container} data-testid="drift-findings">
      {/* Batch action toolbar */}
      {selected.size > 0 && (
        <Toolbar className={styles.toolbar} aria-label="Batch actions">
          <ToolbarButton
            icon={<CheckmarkRegular />}
            onClick={() => handleBatchAction("accept")}
            disabled={loading}
          >
            Accept Selected
          </ToolbarButton>
          <ToolbarButton
            icon={<ArrowUndoRegular />}
            onClick={() => handleBatchAction("revert")}
            disabled={loading}
          >
            Revert Selected
          </ToolbarButton>
          <ToolbarButton
            icon={<EyeOffRegular />}
            onClick={() => openSuppressDialog(Array.from(selected))}
            disabled={loading}
          >
            Suppress Selected
          </ToolbarButton>
          <Text className={styles.selectionCount}>
            {selected.size} of {findings.length} selected
          </Text>
        </Toolbar>
      )}

      {/* Findings table */}
      <Table aria-label="Drift findings">
        <TableHeader>
          <TableRow>
            <TableHeaderCell>
              <Checkbox
                checked={allSelected ? true : selected.size > 0 ? "mixed" : false}
                onChange={toggleAll}
                aria-label="Select all findings"
              />
            </TableHeaderCell>
            <TableHeaderCell>Resource</TableHeaderCell>
            <TableHeaderCell>Property</TableHeaderCell>
            <TableHeaderCell>Expected</TableHeaderCell>
            <TableHeaderCell>Actual</TableHeaderCell>
            <TableHeaderCell>Severity</TableHeaderCell>
            <TableHeaderCell>Status</TableHeaderCell>
            <TableHeaderCell>Actions</TableHeaderCell>
          </TableRow>
        </TableHeader>
        <TableBody>
          {findings.map((finding) => (
            <TableRow
              key={finding.id}
              className={finding.resolved_at ? styles.resolved : undefined}
            >
              <TableCell>
                <Checkbox
                  checked={selected.has(finding.id)}
                  onChange={() => toggleSelect(finding.id)}
                  aria-label={`Select ${resourceName(finding.resource_id)}`}
                />
              </TableCell>
              <TableCell>
                <TableCellLayout>
                  <Text className={styles.truncated} title={finding.resource_id}>
                    {resourceName(finding.resource_id)}
                  </Text>
                </TableCellLayout>
              </TableCell>
              <TableCell>
                <Text>{finding.drift_type}</Text>
              </TableCell>
              <TableCell>
                <Text className={styles.truncated}>
                  {finding.expected_value ? JSON.stringify(finding.expected_value) : "—"}
                </Text>
              </TableCell>
              <TableCell>
                <Text className={styles.truncated}>
                  {finding.actual_value ? JSON.stringify(finding.actual_value) : "—"}
                </Text>
              </TableCell>
              <TableCell>{severityBadge(finding.severity)}</TableCell>
              <TableCell>
                <Text>{statusLabel(finding)}</Text>
              </TableCell>
              <TableCell>
                <div className={styles.actions}>
                  <Button
                    size="small"
                    icon={<CheckmarkRegular />}
                    onClick={() => handleAction(finding.id, "accept")}
                    disabled={loading || !!finding.resolved_at}
                    title="Accept"
                    aria-label="Accept"
                  />
                  <Button
                    size="small"
                    icon={<ArrowUndoRegular />}
                    onClick={() => handleAction(finding.id, "revert")}
                    disabled={loading || !!finding.resolved_at}
                    title="Revert"
                    aria-label="Revert"
                  />
                  <Button
                    size="small"
                    icon={<EyeOffRegular />}
                    onClick={() => openSuppressDialog(finding.id)}
                    disabled={loading || !!finding.resolved_at}
                    title="Suppress"
                    aria-label="Suppress"
                  />
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {/* Suppress dialog */}
      <Dialog open={suppressDialogOpen} onOpenChange={(_e, data) => setSuppressDialogOpen(data.open)}>
        <DialogSurface>
          <DialogBody>
            <DialogTitle>Suppress Drift Finding</DialogTitle>
            <DialogContent>
              <div className={styles.dialogField}>
                <Text className={styles.label}>Justification</Text>
                <Textarea
                  value={justification}
                  onChange={(_e, data) => setJustification(data.value)}
                  placeholder="Explain why this drift is intentional..."
                  rows={3}
                  data-testid="suppress-justification"
                />
              </div>
              <div className={styles.dialogField}>
                <Text className={styles.label}>Expiration</Text>
                <Dropdown
                  value={EXPIRATION_OPTIONS.find((o) => o.value === expirationDays)?.label ?? "30 days"}
                  selectedOptions={[expirationDays]}
                  onOptionSelect={(_e, data) => setExpirationDays(data.optionValue ?? "30")}
                  data-testid="suppress-expiration"
                >
                  {EXPIRATION_OPTIONS.map((opt) => (
                    <Option key={opt.value} value={opt.value}>
                      {opt.label}
                    </Option>
                  ))}
                </Dropdown>
              </div>
            </DialogContent>
            <DialogActions>
              <DialogTrigger disableButtonEnhancement>
                <Button appearance="secondary">Cancel</Button>
              </DialogTrigger>
              <Button
                appearance="primary"
                onClick={handleSuppress}
                disabled={loading}
                data-testid="suppress-confirm"
              >
                Suppress
              </Button>
            </DialogActions>
          </DialogBody>
        </DialogSurface>
      </Dialog>
    </div>
  );
}
