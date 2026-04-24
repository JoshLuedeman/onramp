import {
  Button,
  Combobox,
  Field,
  Input,
  MessageBar,
  MessageBarBody,
  Option,
  Popover,
  PopoverSurface,
  PopoverTrigger,
  Spinner,
  Text,
  Tooltip,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  AddRegular,
  ArrowSortRegular,
  DismissRegular,
  LinkRegular,
  SearchRegular,
  ZoomInRegular,
  ZoomOutRegular,
  ZoomFitRegular,
} from "@fluentui/react-icons";
import { useState } from "react";
import type { WorkloadSummary } from "../../services/api";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface DependencyGraphToolbarProps {
  loading: boolean;
  onRefresh: () => void;
  nodeCount: number;
  nodes: WorkloadSummary[];
  addDepOpen: boolean;
  onAddDepOpenChange: (open: boolean) => void;
  onAddDep: (sourceId: string, targetId: string) => Promise<void>;
  addDepLoading: boolean;
  addDepError: string | null;
  onClearAddDepError: () => void;
  orderLoading: boolean;
  onFetchOrder: () => void;
  selectedNodeId: string | null;
  onClearSelection: () => void;
  searchQuery: string;
  onSearchChange: (value: string) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetZoom: () => void;
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const useStyles = makeStyles({
  toolbar: {
    display: "flex",
    gap: tokens.spacingHorizontalM,
    alignItems: "center",
    flexWrap: "wrap",
  },
  addDepForm: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalM,
    minWidth: "280px",
    padding: tokens.spacingVerticalM,
  },
  addDepFormButtons: {
    display: "flex",
    gap: tokens.spacingHorizontalS,
  },
  zoomControls: {
    display: "flex",
    gap: tokens.spacingHorizontalXS,
    alignItems: "center",
  },
});

// ---------------------------------------------------------------------------
// Add Dependency popover form (internal)
// ---------------------------------------------------------------------------

function AddDepForm({
  nodes,
  onAdd,
  onClose,
  loading,
  error,
}: {
  nodes: WorkloadSummary[];
  onAdd: (sourceId: string, targetId: string) => Promise<void>;
  onClose: () => void;
  loading: boolean;
  error: string | null;
}) {
  const styles = useStyles();
  const [source, setSource] = useState("");
  const [sourceInput, setSourceInput] = useState("");
  const [target, setTarget] = useState("");
  const [targetInput, setTargetInput] = useState("");

  return (
    <div className={styles.addDepForm}>
      <Text weight="semibold">Add Dependency</Text>
      <Field label="From workload">
        <Combobox
          value={sourceInput}
          selectedOptions={source ? [source] : []}
          onOptionSelect={(_, d) => {
            setSource(d.optionValue ?? "");
            setSourceInput(d.optionText ?? "");
          }}
          onChange={(e) => setSourceInput(e.target.value)}
          placeholder="Select source workload"
        >
          {nodes.map((n) => (
            <Option key={n.id} value={n.id}>
              {n.name}
            </Option>
          ))}
        </Combobox>
      </Field>
      <Field label="Depends on">
        <Combobox
          value={targetInput}
          selectedOptions={target ? [target] : []}
          onOptionSelect={(_, d) => {
            setTarget(d.optionValue ?? "");
            setTargetInput(d.optionText ?? "");
          }}
          onChange={(e) => setTargetInput(e.target.value)}
          placeholder="Select target workload"
        >
          {nodes.filter((n) => n.id !== source).map((n) => (
            <Option key={n.id} value={n.id}>
              {n.name}
            </Option>
          ))}
        </Combobox>
      </Field>
      {error && (
        <MessageBar intent="error">
          <MessageBarBody>{error}</MessageBarBody>
        </MessageBar>
      )}
      <div className={styles.addDepFormButtons}>
        <Button
          appearance="primary"
          icon={loading ? <Spinner size="tiny" /> : <LinkRegular />}
          disabled={!source || !target || loading}
          onClick={() => onAdd(source, target)}
        >
          Add
        </Button>
        <Button appearance="subtle" icon={<DismissRegular />} onClick={onClose}>
          Cancel
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DependencyGraphToolbar({
  loading,
  onRefresh,
  nodeCount,
  nodes,
  addDepOpen,
  onAddDepOpenChange,
  onAddDep,
  addDepLoading,
  addDepError,
  onClearAddDepError,
  orderLoading,
  onFetchOrder,
  selectedNodeId,
  onClearSelection,
  searchQuery,
  onSearchChange,
  onZoomIn,
  onZoomOut,
  onResetZoom,
}: DependencyGraphToolbarProps) {
  const styles = useStyles();

  return (
    <div className={styles.toolbar}>
      <Button
        appearance="subtle"
        onClick={onRefresh}
        disabled={loading}
        icon={loading ? <Spinner size="tiny" /> : undefined}
      >
        {loading ? "Loading…" : "Refresh"}
      </Button>

      <Popover
        open={addDepOpen}
        onOpenChange={(_, d) => {
          onAddDepOpenChange(d.open);
          if (!d.open) onClearAddDepError();
        }}
        positioning="below-start"
      >
        <PopoverTrigger>
          <Button
            appearance="primary"
            icon={<AddRegular />}
            disabled={nodeCount < 2}
            aria-label="Add Dependency"
          >
            Add Dependency
          </Button>
        </PopoverTrigger>
        <PopoverSurface>
          <AddDepForm
            nodes={nodes}
            onAdd={onAddDep}
            onClose={() => onAddDepOpenChange(false)}
            loading={addDepLoading}
            error={addDepError}
          />
        </PopoverSurface>
      </Popover>

      <Button
        appearance="subtle"
        icon={orderLoading ? <Spinner size="tiny" /> : <ArrowSortRegular />}
        onClick={onFetchOrder}
        disabled={orderLoading}
        aria-label="Suggest Migration Order"
      >
        Suggest Migration Order
      </Button>

      {selectedNodeId && (
        <Button
          appearance="subtle"
          icon={<DismissRegular />}
          size="small"
          onClick={onClearSelection}
          aria-label="Clear selection"
        >
          Clear selection
        </Button>
      )}

      {/* Search/filter */}
      <Input
        contentBefore={<SearchRegular />}
        placeholder="Filter workloads…"
        value={searchQuery}
        onChange={(_, d) => onSearchChange(d.value)}
        aria-label="Filter workloads by name"
      />

      {/* Zoom controls */}
      <div className={styles.zoomControls}>
        <Tooltip content="Zoom in" relationship="label">
          <Button
            appearance="subtle"
            icon={<ZoomInRegular />}
            size="small"
            onClick={onZoomIn}
            aria-label="Zoom in"
          />
        </Tooltip>
        <Tooltip content="Zoom out" relationship="label">
          <Button
            appearance="subtle"
            icon={<ZoomOutRegular />}
            size="small"
            onClick={onZoomOut}
            aria-label="Zoom out"
          />
        </Tooltip>
        <Tooltip content="Reset zoom" relationship="label">
          <Button
            appearance="subtle"
            icon={<ZoomFitRegular />}
            size="small"
            onClick={onResetZoom}
            aria-label="Reset zoom"
          />
        </Tooltip>
      </div>
    </div>
  );
}
