/**
 * Shared constants, types, and layout helpers for DependencyGraph sub-components.
 */

import { tokens } from "@fluentui/react-components";
import type { WorkloadSummary } from "../../services/api";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const NODE_W = 140;
export const NODE_H = 50;
export const NODE_PADDING_X = 30;
export const NODE_PADDING_Y = 40;
export const COLS = 4;

/** Criticality colour strip — mapped to Fluent UI semantic colour tokens. */
export const CRITICALITY_COLOR: Record<string, string> = {
  "mission-critical": tokens.colorStatusDangerForeground1,
  "business-critical": tokens.colorStatusWarningForeground1,
  "standard": tokens.colorBrandForeground1,
  "dev-test": tokens.colorNeutralForeground3,
};

/** Group background palette — Fluent UI palette tokens for light/dark themes. */
export const GROUP_PALETTE = [
  tokens.colorPaletteBlueBackground2,
  tokens.colorPaletteGreenBackground2,
  tokens.colorPaletteGrapeBackground2,
  tokens.colorPaletteMarigoldBackground2,
  tokens.colorPaletteTealBackground2,
];

/** Criticality → node size multiplier so more critical workloads stand out. */
export const CRITICALITY_SIZE_SCALE: Record<string, number> = {
  "mission-critical": 1.15,
  "business-critical": 1.07,
  standard: 1.0,
  "dev-test": 0.92,
};

/** Migration strategy → colour indicator (small dot on each node). */
export const MIGRATION_STRATEGY_COLOR: Record<string, string> = {
  rehost: tokens.colorPaletteGreenForeground1,
  replatform: tokens.colorPaletteBlueForeground2,
  refactor: tokens.colorPaletteMarigoldForeground1,
  rearchitect: tokens.colorPaletteGrapeForeground2,
  rebuild: tokens.colorStatusDangerForeground1,
  retire: tokens.colorNeutralForeground4,
  retain: tokens.colorNeutralForeground3,
  replace: tokens.colorPaletteRedForeground1,
  unknown: tokens.colorNeutralForeground3,
};

// ---------------------------------------------------------------------------
// Layout types & helpers
// ---------------------------------------------------------------------------

export interface NodeLayout {
  id: string;
  x: number;
  y: number;
  summary: WorkloadSummary;
  /** Size multiplier derived from criticality. */
  scale: number;
}

export function layoutNodes(nodes: WorkloadSummary[]): NodeLayout[] {
  return nodes.map((node, i) => {
    const col = i % COLS;
    const row = Math.floor(i / COLS);
    return {
      id: node.id,
      x: NODE_PADDING_X + col * (NODE_W + NODE_PADDING_X),
      y: NODE_PADDING_Y + row * (NODE_H + NODE_PADDING_Y),
      summary: node,
      scale: CRITICALITY_SIZE_SCALE[node.criticality] ?? 1.0,
    };
  });
}

export function svgDimensions(layouts: NodeLayout[]): { w: number; h: number } {
  if (layouts.length === 0) return { w: 400, h: 200 };
  const maxX = Math.max(...layouts.map((n) => n.x + NODE_W));
  const maxY = Math.max(...layouts.map((n) => n.y + NODE_H));
  return { w: maxX + NODE_PADDING_X, h: maxY + NODE_PADDING_Y };
}

/** Return the centre of a node box for edge attachment. */
export function nodeCentre(layout: NodeLayout): { x: number; y: number } {
  return { x: layout.x + NODE_W / 2, y: layout.y + NODE_H / 2 };
}
