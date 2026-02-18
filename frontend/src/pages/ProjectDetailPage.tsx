import { useNavigate } from "react-router-dom";
import {
  makeStyles,
  tokens,
  Card,
  Badge,
  Button,
  Title1,
  Subtitle1,
  Body1,
  Text,
  Spinner,
} from "@fluentui/react-components";
import {
  ArrowLeftRegular,
  CheckmarkCircleRegular,
  LockClosedRegular,
  PlayRegular,
} from "@fluentui/react-icons";
import { useProject } from "../contexts/ProjectContext";
import type { ProjectStatus } from "../types/project";

type BadgeColor = "informative" | "warning" | "severe" | "success" | "danger";

const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  questionnaire_complete: "Questionnaire Complete",
  architecture_generated: "Architecture Generated",
  compliance_scored: "Compliance Scored",
  bicep_ready: "Bicep Ready",
  deploying: "Deploying",
  deployed: "Deployed",
  failed: "Failed",
};

function getStatusBadgeColor(status: string): BadgeColor {
  switch (status) {
    case "deployed":
      return "success";
    case "deploying":
      return "severe";
    case "failed":
      return "danger";
    case "draft":
      return "informative";
    default:
      return "warning";
  }
}

const STEP_ORDER: ProjectStatus[] = [
  "draft",
  "questionnaire_complete",
  "architecture_generated",
  "compliance_scored",
  "bicep_ready",
  "deploying",
  "deployed",
];

interface Step {
  label: string;
  path: string;
  completedAt: ProjectStatus;
}

const STEPS: Step[] = [
  { label: "Questionnaire", path: "wizard", completedAt: "questionnaire_complete" },
  { label: "Architecture", path: "architecture", completedAt: "architecture_generated" },
  { label: "Compliance", path: "compliance", completedAt: "compliance_scored" },
  { label: "Bicep Preview", path: "bicep", completedAt: "bicep_ready" },
  { label: "Deploy", path: "deploy", completedAt: "deployed" },
];

function getStepStatus(
  stepIndex: number,
  projectStatus: ProjectStatus,
): "complete" | "current" | "locked" {
  const statusIndex = STEP_ORDER.indexOf(projectStatus);
  const stepCompletedIndex = STEP_ORDER.indexOf(STEPS[stepIndex].completedAt);

  if (statusIndex >= stepCompletedIndex) return "complete";
  if (stepIndex === 0 && statusIndex === 0) return "current";
  const prevStepCompletedIndex =
    stepIndex > 0 ? STEP_ORDER.indexOf(STEPS[stepIndex - 1].completedAt) : -1;
  if (statusIndex >= prevStepCompletedIndex && statusIndex < stepCompletedIndex) return "current";
  return "locked";
}

const useStyles = makeStyles({
  container: {
    maxWidth: "800px",
    marginLeft: "auto",
    marginRight: "auto",
    padding: tokens.spacingHorizontalXXL,
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalL,
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalM,
  },
  stepCard: {
    padding: tokens.spacingVerticalM,
  },
  stepRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: `${tokens.spacingVerticalS} 0`,
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
  },
  stepLabel: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
  },
  stepNumber: {
    fontWeight: tokens.fontWeightSemibold,
    minWidth: "24px",
  },
  errorContainer: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: tokens.spacingVerticalM,
    padding: tokens.spacingVerticalXXL,
  },
});

export default function ProjectDetailPage() {
  const styles = useStyles();
  const navigate = useNavigate();
  const { project, loading, error } = useProject();

  if (loading) {
    return (
      <div className={styles.container}>
        <Spinner size="large" label="Loading project..." />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className={styles.container}>
        <div className={styles.errorContainer}>
          <Title1>Project Not Found</Title1>
          <Body1>{error || "The requested project could not be loaded."}</Body1>
          <Button appearance="primary" onClick={() => navigate("/")}>
            Back to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <Button
        appearance="subtle"
        icon={<ArrowLeftRegular />}
        onClick={() => navigate("/")}
      >
        Back to Dashboard
      </Button>

      <div className={styles.header}>
        <Title1>{project.name}</Title1>
        <Badge appearance="filled" color={getStatusBadgeColor(project.status)} size="large">
          {STATUS_LABELS[project.status] ?? project.status}
        </Badge>
      </div>

      {project.description && <Body1>{project.description}</Body1>}

      <Subtitle1>Steps</Subtitle1>

      <Card className={styles.stepCard}>
        {STEPS.map((step, index) => {
          const stepStatus = getStepStatus(index, project.status);
          return (
            <div key={step.path} className={styles.stepRow}>
              <div className={styles.stepLabel}>
                <Text className={styles.stepNumber}>{index + 1}.</Text>
                {stepStatus === "complete" && (
                  <CheckmarkCircleRegular
                    style={{ color: tokens.colorPaletteGreenForeground1 }}
                  />
                )}
                {stepStatus === "locked" && <LockClosedRegular />}
                {stepStatus === "current" && <PlayRegular />}
                <Body1>{step.label}</Body1>
              </div>
              <Button
                appearance={stepStatus === "current" ? "primary" : "subtle"}
                size="small"
                disabled={stepStatus === "locked"}
                onClick={() => navigate(`/projects/${project.id}/${step.path}`)}
              >
                {stepStatus === "complete"
                  ? "Review"
                  : stepStatus === "current"
                    ? "Continue →"
                    : "Locked"}
              </Button>
            </div>
          );
        })}
      </Card>
    </div>
  );
}
