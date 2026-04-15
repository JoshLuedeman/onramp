import {
  Badge,
  Button,
  Card,
  Text,
  ProgressBar,
  makeStyles,
  tokens,
  Dialog,
  DialogTrigger,
  DialogSurface,
  DialogTitle,
  DialogBody,
  DialogActions,
  DialogContent,
} from "@fluentui/react-components";
import {
  ErrorCircleRegular,
  WarningRegular,
  InfoRegular,
  CheckmarkCircleRegular,
  WrenchRegular,
} from "@fluentui/react-icons";
import type { GapAnalysisResponse } from "../../services/api";

const useStyles = makeStyles({
  bar: {
    padding: "16px 20px",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  row: {
    display: "flex",
    alignItems: "center",
    gap: "16px",
    flexWrap: "wrap",
  },
  title: {
    fontSize: tokens.fontSizeBase600,
    fontWeight: tokens.fontWeightSemibold,
  },
  counts: {
    display: "flex",
    gap: "12px",
    alignItems: "center",
    flexWrap: "wrap",
  },
  countItem: {
    display: "flex",
    alignItems: "center",
    gap: "4px",
  },
  healthSection: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    flex: 1,
    minWidth: "200px",
  },
  healthScore: {
    fontSize: tokens.fontSizeBase500,
    fontWeight: tokens.fontWeightBold,
    minWidth: "48px",
  },
  progressWrap: {
    flex: 1,
  },
});

interface GapSummaryBarProps {
  result: GapAnalysisResponse;
  onFixAll?: () => void;
}

function healthColor(score: number): "success" | "warning" | "error" {
  if (score >= 80) return "success";
  if (score >= 50) return "warning";
  return "error";
}

function computeHealthScore(result: GapAnalysisResponse): number {
  const total = result.total_findings;
  if (total === 0) return 100;
  const weighted =
    result.critical_count * 4 +
    result.high_count * 3 +
    result.medium_count * 2 +
    result.low_count * 1;
  const maxWeighted = total * 4;
  return Math.max(0, Math.round(100 - (weighted / maxWeighted) * 100));
}

export default function GapSummaryBar({ result, onFixAll }: GapSummaryBarProps) {
  const styles = useStyles();
  const health = computeHealthScore(result);
  const color = healthColor(health);

  return (
    <Card className={styles.bar}>
      <div className={styles.row}>
        <Text className={styles.title}>
          <WrenchRegular /> Gap Analysis Summary
        </Text>
        <div className={styles.counts}>
          <div className={styles.countItem}>
            <ErrorCircleRegular color={tokens.colorPaletteRedForeground1} />
            <Badge color="danger" appearance="filled">
              {result.critical_count} Critical
            </Badge>
          </div>
          <div className={styles.countItem}>
            <WarningRegular color={tokens.colorPaletteMarigoldForeground2} />
            <Badge color="warning" appearance="filled">
              {result.high_count} High
            </Badge>
          </div>
          <div className={styles.countItem}>
            <InfoRegular color={tokens.colorPaletteBlueForeground2} />
            <Badge color="informative" appearance="filled">
              {result.medium_count} Medium
            </Badge>
          </div>
          <div className={styles.countItem}>
            <CheckmarkCircleRegular color={tokens.colorNeutralForeground3} />
            <Badge color="subtle" appearance="filled">
              {result.low_count} Low
            </Badge>
          </div>
        </div>
      </div>

      <div className={styles.row}>
        <div className={styles.healthSection}>
          <Text className={styles.healthScore}>{health}%</Text>
          <div className={styles.progressWrap}>
            <Text size={200}>Overall Health</Text>
            <ProgressBar
              value={health / 100}
              color={color}
            />
          </div>
        </div>

        <Dialog>
          <DialogTrigger disableButtonEnhancement>
            <Button appearance="primary" icon={<WrenchRegular />}>
              Fix All
            </Button>
          </DialogTrigger>
          <DialogSurface>
            <DialogBody>
              <DialogTitle>Confirm Fix All</DialogTitle>
              <DialogContent>
                This will schedule remediation for all {result.total_findings} findings.
                Are you sure you want to proceed?
              </DialogContent>
              <DialogActions>
                <DialogTrigger disableButtonEnhancement>
                  <Button appearance="secondary">Cancel</Button>
                </DialogTrigger>
                <DialogTrigger disableButtonEnhancement>
                  <Button
                    appearance="primary"
                    onClick={onFixAll}
                  >
                    Confirm
                  </Button>
                </DialogTrigger>
              </DialogActions>
            </DialogBody>
          </DialogSurface>
        </Dialog>
      </div>
    </Card>
  );
}
