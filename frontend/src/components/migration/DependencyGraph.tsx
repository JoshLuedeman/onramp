/**
 * DependencyGraph — interactive SVG-based workload dependency visualizer.
 * Uses SVG/HTML5 only (no external graph libraries).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Badge,
  Button,
  Combobox,
  Field,
  MessageBar,
  MessageBarBody,
  Option,
  Popover,
  PopoverSurface,
  PopoverTrigger,
  Spinner,
  Text,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  AddRegular,
  ArrowSortRegular,
  DismissRegular,
  LinkRegular,
} from "@fluentui/react-icons";
import type {
  DependencyEdge,
  DependencyGraph as DependencyGraphData,
  MigrationOrderResponse,
  WorkloadSummary,
} from "../../services/api";
import { api } from "../../services/api";

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const useStyles = makeStyles({
  root: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalL,
  },
  toolbar: {
    display: "flex",
    gap: tokens.spacingHorizontalM,
    alignItems: "center",
    flexWrap: "wrap",
  },
  svgContainer: {
    border: `1px solid ${tokens.colorNeutralStroke1}`,
    borderRadius: tokens.borderRadiusMedium,
    backgroundColor: tokens.colorNeutralBackground2,
    overflow: "auto",
    minHeight: "400px",
  },
  legend: {
    display: "flex",
    gap: tokens.spacingHorizontalL,
    flexWrap: "wrap",
    alignItems: "center",
  },
  legendItem: {
    display: "flex",
    gap: tokens.spacingHorizontalXS,
    alignItems: "center",
  },
  legendSwatch: {
    width: "16px",
    height: "16px",
    borderRadius: tokens.borderRadiusSmall,
  },
  orderList: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXS,
  },
  orderItem: {
    display: "flex",
    gap: tokens.spacingHorizontalS,
    alignItems: "center",
    padding: `${tokens.spacingVerticalXS} ${tokens.spacingHorizontalS}`,
    backgroundColor: tokens.colorNeutralBackground1,
    borderRadius: tokens.borderRadiusMedium,
    border: `1px solid ${tokens.colorNeutralStroke1}`,
  },
  addDepForm: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalM,
    minWidth: "280px",
    padding: tokens.spacingVerticalM,
  },
  detailPopover: {
    padding: tokens.spacingVerticalM,
    minWidth: "200px",
  },
  detailRow: {
    display: "flex",
    gap: tokens.spacingHorizontalXS,
    alignItems: "baseline",
  },
  emptyState: {
    padding: tokens.spacingVerticalXXL,
    textAlign: "center",
    color: tokens.colorNeutralForeground3,
  },
});

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const NODE_W = 140;
const NODE_H = 50;
const NODE_PADDING_X = 30;
const NODE_PADDING_Y = 40;
const COLS = 4;

const CRITICALITY_COLOR: Record<string, string> = {
  "mission-critical": "#C50F1F",   // danger red
  "business-critical": "#BC5700",  // warning amber
  "standard": "#0F6CBD",           // brand blue
  "dev-test": "#616161",           // neutral grey
};

const GROUP_PALETTE = [
  "rgba(0,120,212,0.08)",
  "rgba(0,164,120,0.08)",
  "rgba(177,70,194,0.08)",
  "rgba(255,140,0,0.08)",
  "rgba(0,83,128,0.08)",
];

// ---------------------------------------------------------------------------
// Layout helpers
// ---------------------------------------------------------------------------

interface NodeLayout {
  id: string;
  x: number;
  y: number;
  summary: WorkloadSummary;
}

function layoutNodes(nodes: WorkloadSummary[]): NodeLayout[] {
  return nodes.map((node, i) => {
    const col = i % COLS;
    const row = Math.floor(i / COLS);
    return {
      id: node.id,
      x: NODE_PADDING_X + col * (NODE_W + NODE_PADDING_X),
      y: NODE_PADDING_Y + row * (NODE_H + NODE_PADDING_Y),
      summary: node,
    };
  });
}

function svgDimensions(layouts: NodeLayout[]): { w: number; h: number } {
  if (layouts.length === 0) return { w: 400, h: 200 };
  const maxX = Math.max(...layouts.map((n) => n.x + NODE_W));
  const maxY = Math.max(...layouts.map((n) => n.y + NODE_H));
  return { w: maxX + NODE_PADDING_X, h: maxY + NODE_PADDING_Y };
}

// Return the centre of a node box for edge attachment
function nodeCentre(layout: NodeLayout): { x: number; y: number } {
  return { x: layout.x + NODE_W / 2, y: layout.y + NODE_H / 2 };
}

// ---------------------------------------------------------------------------
// SVG Edge (arrow)
// ---------------------------------------------------------------------------

interface EdgeProps {
  from: NodeLayout;
  to: NodeLayout;
  inCycle: boolean;
}

function GraphEdge({ from, to, inCycle }: EdgeProps) {
  const fc = nodeCentre(from);
  const tc = nodeCentre(to);

  // Offset to edge of box rather than centre
  const dx = tc.x - fc.x;
  const dy = tc.y - fc.y;
  const len = Math.sqrt(dx * dx + dy * dy) || 1;
  const ux = dx / len;
  const uy = dy / len;
  const halfW = NODE_W / 2 + 4;
  const halfH = NODE_H / 2 + 4;

  // Find exit point on source box border
  const scaleSource = Math.min(halfW / Math.abs(ux || 0.001), halfH / Math.abs(uy || 0.001));
  const x1 = fc.x + ux * scaleSource;
  const y1 = fc.y + uy * scaleSource;

  // Find entry point on target box border
  const scaleDest = Math.min(halfW / Math.abs(ux || 0.001), halfH / Math.abs(uy || 0.001));
  const x2 = tc.x - ux * scaleDest;
  const y2 = tc.y - uy * scaleDest;

  const color = inCycle ? "#C50F1F" : tokens.colorNeutralForeground3;
  const strokeWidth = inCycle ? 2 : 1.5;

  return (
    <line
      x1={x1}
      y1={y1}
      x2={x2}
      y2={y2}
      stroke={color}
      strokeWidth={strokeWidth}
      markerEnd={inCycle ? "url(#arrowCycle)" : "url(#arrow)"}
      opacity={0.85}
    />
  );
}

// ---------------------------------------------------------------------------
// SVG Node box
// ---------------------------------------------------------------------------

interface NodeBoxProps {
  layout: NodeLayout;
  isSelected: boolean;
  groupColor?: string;
  inCycle: boolean;
  onClick: (id: string) => void;
}

function NodeBox({ layout, isSelected, groupColor, inCycle, onClick }: NodeBoxProps) {
  const fill = groupColor ?? tokens.colorNeutralBackground1;
  const borderColor = inCycle
    ? "#C50F1F"
    : isSelected
      ? tokens.colorBrandStroke1
      : tokens.colorNeutralStroke1;
  const critColor = CRITICALITY_COLOR[layout.summary.criticality] ?? "#0F6CBD";

  const shortName =
    layout.summary.name.length > 16
      ? layout.summary.name.slice(0, 14) + "…"
      : layout.summary.name;

  return (
    <g
      transform={`translate(${layout.x},${layout.y})`}
      onClick={() => onClick(layout.id)}
      style={{ cursor: "pointer" }}
      role="button"
      aria-label={`Workload node: ${layout.summary.name}`}
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onClick(layout.id)}
    >
      {/* Group background — drawn before rect */}
      {groupColor && (
        <rect
          x={-6}
          y={-6}
          width={NODE_W + 12}
          height={NODE_H + 12}
          fill={fill}
          rx={6}
          ry={6}
        />
      )}
      <rect
        width={NODE_W}
        height={NODE_H}
        fill={tokens.colorNeutralBackground1}
        stroke={borderColor}
        strokeWidth={isSelected ? 2 : 1}
        rx={4}
        ry={4}
      />
      {/* Criticality colour strip */}
      <rect width={6} height={NODE_H} fill={critColor} rx={3} ry={3} />
      <text
        x={14}
        y={20}
        fontSize={12}
        fontWeight="600"
        fill={tokens.colorNeutralForeground1}
        style={{ userSelect: "none" }}
      >
        {shortName}
      </text>
      <text
        x={14}
        y={36}
        fontSize={10}
        fill={tokens.colorNeutralForeground3}
        style={{ userSelect: "none" }}
      >
        {layout.summary.criticality}
      </text>
    </g>
  );
}

// ---------------------------------------------------------------------------
// Add Dependency popover form
// ---------------------------------------------------------------------------

interface AddDepFormProps {
  nodes: WorkloadSummary[];
  onAdd: (sourceId: string, targetId: string) => Promise<void>;
  onClose: () => void;
  loading: boolean;
  error: string | null;
}

function AddDepForm({ nodes, onAdd, onClose, loading, error }: AddDepFormProps) {
  const styles = useStyles();
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");

  return (
    <div className={styles.addDepForm}>
      <Text weight="semibold">Add Dependency</Text>
      <Field label="From workload">
        <Combobox
          value={nodes.find((n) => n.id === source)?.name ?? ""}
          onOptionSelect={(_, d) => setSource(d.optionValue ?? "")}
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
          value={nodes.find((n) => n.id === target)?.name ?? ""}
          onOptionSelect={(_, d) => setTarget(d.optionValue ?? "")}
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
      <div style={{ display: "flex", gap: "8px" }}>
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
// Main component
// ---------------------------------------------------------------------------

interface DependencyGraphProps {
  projectId: string;
}

export default function DependencyGraph({ projectId }: DependencyGraphProps) {
  const styles = useStyles();

  const [graph, setGraph] = useState<DependencyGraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [migrationOrder, setMigrationOrder] = useState<MigrationOrderResponse | null>(null);
  const [orderLoading, setOrderLoading] = useState(false);
  const [orderError, setOrderError] = useState<string | null>(null);

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [addDepOpen, setAddDepOpen] = useState(false);
  const [addDepLoading, setAddDepLoading] = useState(false);
  const [addDepError, setAddDepError] = useState<string | null>(null);

  // Ref for selected node (could be used for future popover positioning)
  const detailAnchorRef = useRef<SVGGElement | null>(null);

  const fetchGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.workloads.getDependencyGraph(projectId);
      setGraph(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dependency graph");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  const fetchOrder = async () => {
    setOrderLoading(true);
    setOrderError(null);
    try {
      const data = await api.workloads.getMigrationOrder(projectId);
      setMigrationOrder(data);
    } catch (err) {
      setOrderError(err instanceof Error ? err.message : "Failed to get migration order");
    } finally {
      setOrderLoading(false);
    }
  };

  const handleAddDep = async (sourceId: string, targetId: string) => {
    setAddDepLoading(true);
    setAddDepError(null);
    try {
      await api.workloads.addDependency(sourceId, targetId);
      setAddDepOpen(false);
      await fetchGraph();
    } catch (err) {
      setAddDepError(err instanceof Error ? err.message : "Failed to add dependency");
    } finally {
      setAddDepLoading(false);
    }
  };

  // Build a cycle-node lookup set
  const cycleNodes = new Set<string>();
  (graph?.circular_dependencies ?? []).forEach((cycle) =>
    cycle.forEach((id) => cycleNodes.add(id)),
  );

  // Build group-colour map (node → colour)
  const groupColorMap = new Map<string, string>();
  (graph?.migration_groups ?? []).forEach((group, idx) => {
    if (group.length > 1) {
      const color = GROUP_PALETTE[idx % GROUP_PALETTE.length];
      group.forEach((id) => groupColorMap.set(id, color));
    }
  });

  // Build edge lookup for cycle detection
  const cycleEdgeSet = new Set<string>();
  (graph?.circular_dependencies ?? []).forEach((cycle) => {
    for (let i = 0; i < cycle.length; i++) {
      cycleEdgeSet.add(`${cycle[i]}->${cycle[(i + 1) % cycle.length]}`);
    }
  });

  const isEdgeInCycle = (edge: DependencyEdge) =>
    cycleEdgeSet.has(`${edge.source}->${edge.target}`);

  const layouts = layoutNodes(graph?.nodes ?? []);
  const layoutMap = new Map<string, NodeLayout>(layouts.map((l) => [l.id, l]));
  const { w: svgW, h: svgH } = svgDimensions(layouts);

  const selectedNode = graph?.nodes.find((n) => n.id === selectedNodeId);

  const handleNodeClick = (id: string) => {
    setSelectedNodeId((prev) => (prev === id ? null : id));
  };

  return (
    <div className={styles.root}>
      {/* Toolbar */}
      <div className={styles.toolbar}>
        <Button
          appearance="subtle"
          onClick={fetchGraph}
          disabled={loading}
          icon={loading ? <Spinner size="tiny" /> : undefined}
        >
          {loading ? "Loading…" : "Refresh"}
        </Button>

        <Popover
          open={addDepOpen}
          onOpenChange={(_, d) => {
            setAddDepOpen(d.open);
            if (!d.open) setAddDepError(null);
          }}
          positioning="below-start"
        >
          <PopoverTrigger>
            <Button
              appearance="primary"
              icon={<AddRegular />}
              disabled={!graph || graph.nodes.length < 2}
              aria-label="Add Dependency"
            >
              Add Dependency
            </Button>
          </PopoverTrigger>
          <PopoverSurface>
            {graph && (
              <AddDepForm
                nodes={graph.nodes}
                onAdd={handleAddDep}
                onClose={() => setAddDepOpen(false)}
                loading={addDepLoading}
                error={addDepError}
              />
            )}
          </PopoverSurface>
        </Popover>

        <Button
          appearance="subtle"
          icon={orderLoading ? <Spinner size="tiny" /> : <ArrowSortRegular />}
          onClick={fetchOrder}
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
            onClick={() => setSelectedNodeId(null)}
            aria-label="Clear selection"
          >
            Clear selection
          </Button>
        )}
      </div>

      {/* Errors */}
      {error && (
        <MessageBar intent="error">
          <MessageBarBody>{error}</MessageBarBody>
        </MessageBar>
      )}
      {orderError && (
        <MessageBar intent="warning">
          <MessageBarBody>{orderError}</MessageBarBody>
        </MessageBar>
      )}
      {graph && graph.circular_dependencies.length > 0 && (
        <MessageBar intent="error">
          <MessageBarBody>
            ⚠ Circular dependencies detected:{" "}
            {graph.circular_dependencies.map((cycle) => cycle.join(" → ")).join("; ")}
          </MessageBarBody>
        </MessageBar>
      )}

      {/* Legend */}
      <div className={styles.legend}>
        {Object.entries(CRITICALITY_COLOR).map(([level, color]) => (
          <div key={level} className={styles.legendItem}>
            <div
              className={styles.legendSwatch}
              style={{ backgroundColor: color }}
              aria-hidden="true"
            />
            <Text size={200}>{level}</Text>
          </div>
        ))}
        <div className={styles.legendItem}>
          <div
            className={styles.legendSwatch}
            style={{ backgroundColor: "#C50F1F", border: "2px solid #C50F1F" }}
            aria-hidden="true"
          />
          <Text size={200}>circular dependency</Text>
        </div>
        <div className={styles.legendItem}>
          <div
            className={styles.legendSwatch}
            style={{ backgroundColor: GROUP_PALETTE[0] }}
            aria-hidden="true"
          />
          <Text size={200}>migration group</Text>
        </div>
      </div>

      {/* SVG Graph */}
      <div className={styles.svgContainer} aria-label="Dependency graph">
        {graph === null && !loading && (
          <div className={styles.emptyState}>
            <Text>No data loaded yet.</Text>
          </div>
        )}
        {graph !== null && graph.nodes.length === 0 && (
          <div className={styles.emptyState}>
            <Text>No workloads in this project yet. Import workloads first.</Text>
          </div>
        )}
        {graph !== null && graph.nodes.length > 0 && (
          <svg
            width={svgW}
            height={svgH}
            style={{ display: "block" }}
            aria-label="Workload dependency graph SVG"
          >
            <defs>
              <marker
                id="arrow"
                viewBox="0 0 10 10"
                refX="9"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" fill={tokens.colorNeutralForeground3} />
              </marker>
              <marker
                id="arrowCycle"
                viewBox="0 0 10 10"
                refX="9"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#C50F1F" />
              </marker>
            </defs>

            {/* Edges */}
            {graph.edges.map((edge) => {
              const from = layoutMap.get(edge.source);
              const to = layoutMap.get(edge.target);
              if (!from || !to) return null;
              return (
                <GraphEdge
                  key={`${edge.source}-${edge.target}`}
                  from={from}
                  to={to}
                  inCycle={isEdgeInCycle(edge)}
                />
              );
            })}

            {/* Nodes */}
            {layouts.map((layout) => (
              <g key={layout.id} ref={layout.id === selectedNodeId ? detailAnchorRef : undefined}>
                <NodeBox
                  layout={layout}
                  isSelected={layout.id === selectedNodeId}
                  groupColor={groupColorMap.get(layout.id)}
                  inCycle={cycleNodes.has(layout.id)}
                  onClick={handleNodeClick}
                />
              </g>
            ))}
          </svg>
        )}
      </div>

      {/* Node detail panel */}
      {selectedNode && (
        <div
          style={{
            padding: tokens.spacingVerticalM,
            backgroundColor: tokens.colorNeutralBackground1,
            border: `1px solid ${tokens.colorNeutralStroke1}`,
            borderRadius: tokens.borderRadiusMedium,
          }}
          aria-label={`Details for ${selectedNode.name}`}
        >
          <Text weight="semibold" size={400}>
            {selectedNode.name}
          </Text>
          <div style={{ marginTop: tokens.spacingVerticalS, display: "flex", flexDirection: "column", gap: tokens.spacingVerticalXS }}>
            <div className={styles.detailRow}>
              <Text size={200} style={{ color: tokens.colorNeutralForeground3 }}>Criticality:</Text>
              <Badge
                appearance="tint"
                color={
                  selectedNode.criticality === "mission-critical"
                    ? "danger"
                    : selectedNode.criticality === "business-critical"
                      ? "warning"
                      : "informative"
                }
                size="small"
              >
                {selectedNode.criticality}
              </Badge>
            </div>
            <div className={styles.detailRow}>
              <Text size={200} style={{ color: tokens.colorNeutralForeground3 }}>Migration strategy:</Text>
              <Text size={200}>{selectedNode.migration_strategy}</Text>
            </div>
            <div className={styles.detailRow}>
              <Text size={200} style={{ color: tokens.colorNeutralForeground3 }}>In cycle:</Text>
              <Text size={200}>{cycleNodes.has(selectedNode.id) ? "⚠ Yes" : "No"}</Text>
            </div>
            <div className={styles.detailRow}>
              <Text size={200} style={{ color: tokens.colorNeutralForeground3 }}>Depends on:</Text>
              <Text size={200}>
                {(graph?.edges ?? [])
                  .filter((e) => e.source === selectedNode.id)
                  .map((e) => graph?.nodes.find((n) => n.id === e.target)?.name ?? e.target)
                  .join(", ") || "—"}
              </Text>
            </div>
            <div className={styles.detailRow}>
              <Text size={200} style={{ color: tokens.colorNeutralForeground3 }}>Required by:</Text>
              <Text size={200}>
                {(graph?.edges ?? [])
                  .filter((e) => e.target === selectedNode.id)
                  .map((e) => graph?.nodes.find((n) => n.id === e.source)?.name ?? e.source)
                  .join(", ") || "—"}
              </Text>
            </div>
          </div>
        </div>
      )}

      {/* Migration order */}
      {migrationOrder && (
        <div style={{ display: "flex", flexDirection: "column", gap: tokens.spacingVerticalS }}>
          <Text weight="semibold" size={400}>
            Suggested Migration Order
          </Text>
          {migrationOrder.has_circular && (
            <MessageBar intent="warning">
              <MessageBarBody>
                Circular dependencies detected — order may be incomplete.
              </MessageBarBody>
            </MessageBar>
          )}
          {migrationOrder.order.length === 0 && (
            <Text style={{ color: tokens.colorNeutralForeground3 }}>
              Cannot determine order due to circular dependencies.
            </Text>
          )}
          <div className={styles.orderList}>
            {migrationOrder.order.map((id, idx) => (
              <div key={id} className={styles.orderItem}>
                <Badge appearance="filled" size="small" color="brand">
                  {idx + 1}
                </Badge>
                <Text>{migrationOrder.workload_names[id] ?? id}</Text>
                {cycleNodes.has(id) && (
                  <Badge appearance="tint" color="danger" size="small">
                    cycle
                  </Badge>
                )}
              </div>
            ))}
          </div>
          {migrationOrder.migration_groups.length > 0 && (
            <>
              <Text weight="semibold" size={300} style={{ marginTop: tokens.spacingVerticalS }}>
                Migration Groups
              </Text>
              {migrationOrder.migration_groups.map((group, idx) => (
                <div key={idx} className={styles.orderItem}>
                  <Badge appearance="tint" size="small">Group {idx + 1}</Badge>
                  <Text>
                    {group
                      .map((id) => migrationOrder.workload_names[id] ?? id)
                      .join(", ")}
                  </Text>
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}

