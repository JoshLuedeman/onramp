import { useState, useEffect, useCallback } from "react";
import { useParams } from "react-router-dom";
import {
  makeStyles,
  tokens,
  Button,
  Title1,
  Subtitle1,
  Body1,
  Dropdown,
  Option,
  Input,
  Spinner,
  MessageBar,
  MessageBarBody,
  Card,
} from "@fluentui/react-components";
import {
  PlayRegular,
  ArrowDownloadRegular,
  CheckmarkCircleRegular,
} from "@fluentui/react-icons";
import { api } from "../services/api";
import type {
  WaveResponse,
  ValidationWarning,
} from "../services/api";
import WaveTimeline from "../components/migration/WaveTimeline";

const useStyles = makeStyles({
  container: {
    maxWidth: "1200px",
    marginLeft: "auto",
    marginRight: "auto",
    padding: tokens.spacingHorizontalXXL,
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalL,
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  controls: {
    display: "flex",
    gap: tokens.spacingHorizontalM,
    alignItems: "flex-end",
    flexWrap: "wrap",
  },
  field: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXS,
  },
  actions: {
    display: "flex",
    gap: tokens.spacingHorizontalS,
  },
  validationPanel: {
    padding: tokens.spacingVerticalM,
  },
});

const STRATEGY_OPTIONS = [
  { value: "complexity_first", label: "Simplest First" },
  { value: "priority_first", label: "Critical First" },
];

export default function MigrationPage() {
  const styles = useStyles();
  const { projectId } = useParams<{ projectId: string }>();
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [strategy, setStrategy] = useState("complexity_first");
  const [maxWaveSize, setMaxWaveSize] = useState<string>("");
  const [waves, setWaves] = useState<WaveResponse[]>([]);
  const [warnings, setWarnings] = useState<ValidationWarning[]>([]);

  const loadPlan = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.migration.getWaves(projectId);
      setWaves(data.waves);
      setWarnings(data.warnings);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load plan");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadPlan();
  }, [loadPlan]);

  const handleGenerate = useCallback(async () => {
    if (!projectId) return;
    setGenerating(true);
    setError(null);
    try {
      const size = maxWaveSize ? parseInt(maxWaveSize, 10) : undefined;
      const data = await api.migration.generateWaves({
        project_id: projectId,
        strategy,
        max_wave_size: size && !isNaN(size) ? size : null,
        plan_name: "Migration Plan",
      });
      setWaves(data.waves);
      setWarnings(data.warnings);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate waves");
    } finally {
      setGenerating(false);
    }
  }, [projectId, strategy, maxWaveSize]);

  const handleMoveWorkload = useCallback(
    async (workloadId: string, targetWaveId: string, position: number) => {
      try {
        const data = await api.migration.moveWorkload({
          workload_id: workloadId,
          target_wave_id: targetWaveId,
          position,
        });
        setWaves(data.waves);
        setWarnings(data.warnings);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to move workload",
        );
      }
    },
    [],
  );

  const handleReorder = useCallback(
    (waveId: string, workloadId: string, direction: "up" | "down") => {
      setWaves((prev) => {
        const updated = prev.map((wave) => {
          if (wave.id !== waveId) return wave;
          const wls = [...wave.workloads];
          const idx = wls.findIndex((wl) => wl.workload_id === workloadId);
          if (idx < 0) return wave;
          const newIdx = direction === "up" ? idx - 1 : idx + 1;
          if (newIdx < 0 || newIdx >= wls.length) return wave;
          [wls[idx], wls[newIdx]] = [wls[newIdx], wls[idx]];
          return { ...wave, workloads: wls };
        });

        // Persist the new position via API
        const wave = updated.find((w) => w.id === waveId);
        if (wave) {
          const targetIdx = wave.workloads.findIndex(
            (w) => w.workload_id === workloadId,
          );
          if (targetIdx >= 0) {
            api.migration
              .moveWorkload({
                workload_id: workloadId,
                target_wave_id: waveId,
                position: targetIdx,
              })
              .catch((err: unknown) => {
                setError(
                  err instanceof Error
                    ? err.message
                    : "Failed to reorder workload",
                );
              });
          }
        }

        return updated;
      });
    },
    [],
  );

  const handleValidate = useCallback(async () => {
    if (!projectId) return;
    setError(null);
    try {
      const data = await api.migration.validatePlan(projectId);
      setWarnings(data.warnings);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to validate plan",
      );
    }
  }, [projectId]);

  const handleExport = useCallback(
    async (format: "csv" | "markdown") => {
      if (!projectId) return;
      try {
        const blob = await api.migration.exportPlan(projectId, format);
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `migration-plan.${format === "csv" ? "csv" : "md"}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to export plan",
        );
      }
    },
    [projectId],
  );

  if (loading) {
    return (
      <div className={styles.container}>
        <Spinner size="large" label="Loading migration plan..." />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Title1>Migration Wave Planner</Title1>
      </div>

      <div className={styles.controls}>
        <div className={styles.field}>
          <Body1>Strategy</Body1>
          <Dropdown
            value={
              STRATEGY_OPTIONS.find((o) => o.value === strategy)?.label ??
              "Simplest First"
            }
            selectedOptions={[strategy]}
            onOptionSelect={(_e, data) => {
              if (data.optionValue) setStrategy(data.optionValue);
            }}
            data-testid="strategy-dropdown"
          >
            {STRATEGY_OPTIONS.map((opt) => (
              <Option key={opt.value} value={opt.value}>
                {opt.label}
              </Option>
            ))}
          </Dropdown>
        </div>

        <div className={styles.field}>
          <Body1>Max wave size</Body1>
          <Input
            type="number"
            placeholder="Unlimited"
            value={maxWaveSize}
            onChange={(_e, data) => setMaxWaveSize(data.value)}
            data-testid="max-wave-size"
          />
        </div>

        <Button
          appearance="primary"
          icon={<PlayRegular />}
          onClick={handleGenerate}
          disabled={generating}
          data-testid="generate-btn"
        >
          {generating ? "Generating..." : "Generate Waves"}
        </Button>
      </div>

      {error && (
        <MessageBar intent="error">
          <MessageBarBody>{error}</MessageBarBody>
        </MessageBar>
      )}

      <Subtitle1>Wave Timeline</Subtitle1>

      <WaveTimeline
        waves={waves}
        warnings={warnings}
        onMoveWorkload={handleMoveWorkload}
        onReorder={handleReorder}
      />

      {waves.length > 0 && (
        <div className={styles.actions}>
          <Button
            icon={<CheckmarkCircleRegular />}
            onClick={handleValidate}
            data-testid="validate-btn"
          >
            Validate Plan
          </Button>
          <Button
            icon={<ArrowDownloadRegular />}
            onClick={() => handleExport("csv")}
            data-testid="export-csv-btn"
          >
            Export CSV
          </Button>
          <Button
            icon={<ArrowDownloadRegular />}
            onClick={() => handleExport("markdown")}
            data-testid="export-md-btn"
          >
            Export Markdown
          </Button>
        </div>
      )}

      {warnings.length > 0 && (
        <Card className={styles.validationPanel}>
          <Subtitle1>Validation Warnings ({warnings.length})</Subtitle1>
          {warnings.map((w, idx) => (
            <MessageBar key={`vw-${idx}`} intent="warning">
              <MessageBarBody>{w.message}</MessageBarBody>
            </MessageBar>
          ))}
        </Card>
      )}
    </div>
  );
}
