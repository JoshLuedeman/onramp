import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Title1,
  Title2,
  Subtitle2,
  Body1,
  Button,
  Card,
  CardHeader,
  Badge,
  Table,
  TableHeader,
  TableRow,
  TableHeaderCell,
  TableBody,
  TableCell,
  Spinner,
  Dialog,
  DialogTrigger,
  DialogSurface,
  DialogTitle,
  DialogBody,
  DialogActions,
  Input,
  Textarea,
  Field,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  AddRegular,
  DeleteRegular,
  PlayRegular,
  EyeRegular,
  ArrowClockwiseRegular,
} from "@fluentui/react-icons";
import { DonutChart } from "@fluentui/react-charting";
import { api } from "../services/api";
import type { Project, ProjectStats } from "../types/project";

const STATUS_COLORS: Record<string, string> = {
  draft: "#0078d4",
  questionnaire_complete: "#00b7c3",
  architecture_generated: "#8764b8",
  compliance_scored: "#e3008c",
  bicep_ready: "#ffc832",
  deploying: "#ff8c00",
  deployed: "#107c10",
  failed: "#d13438",
};

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

type BadgeColor =
  | "informative"
  | "warning"
  | "severe"
  | "success"
  | "danger";

function getStatusBadgeColor(status: string): BadgeColor {
  switch (status) {
    case "draft":
      return "informative";
    case "questionnaire_complete":
    case "architecture_generated":
    case "compliance_scored":
    case "bicep_ready":
      return "warning";
    case "deploying":
      return "severe";
    case "deployed":
      return "success";
    case "failed":
      return "danger";
    default:
      return "informative";
  }
}

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXXL,
    padding: tokens.spacingHorizontalXXL,
    maxWidth: "1200px",
    marginLeft: "auto",
    marginRight: "auto",
    width: "100%",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "wrap",
    gap: tokens.spacingHorizontalM,
  },
  headerActions: {
    display: "flex",
    gap: tokens.spacingHorizontalS,
  },
  cardsRow: {
    display: "flex",
    gap: tokens.spacingHorizontalL,
    flexWrap: "wrap",
  },
  statCard: {
    flex: "1 1 200px",
    minWidth: "180px",
    padding: tokens.spacingVerticalL,
  },
  statValue: {
    color: tokens.colorBrandForeground1,
    marginTop: tokens.spacingVerticalS,
  },
  chartsRow: {
    display: "flex",
    gap: tokens.spacingHorizontalL,
    flexWrap: "wrap",
  },
  chartCard: {
    flex: "1 1 400px",
    minWidth: "300px",
    padding: tokens.spacingVerticalL,
  },
  emptyState: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: tokens.spacingVerticalXXXL,
    gap: tokens.spacingVerticalM,
  },
  spinnerContainer: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    minHeight: "400px",
  },
  dialogField: {
    marginBottom: tokens.spacingVerticalM,
  },
});

export default function DashboardPage() {
  const styles = useStyles();
  const navigate = useNavigate();

  const [projects, setProjects] = useState<Project[]>([]);
  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [creating, setCreating] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [projectsRes, statsRes] = await Promise.all([
        api.projects.list(),
        api.projects.getStats(),
      ]);
      setProjects(projectsRes.projects);
      setStats(statsRes);
    } catch {
      // Data will remain empty on error
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await api.projects.create({
        name: newName.trim(),
        description: newDescription.trim() || undefined,
      });
      setNewName("");
      setNewDescription("");
      setDialogOpen(false);
      await loadData();
    } catch {
      // Creation failed silently
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.projects.delete(id);
      await loadData();
    } catch {
      // Deletion failed silently
    }
  };

  const handleNavigate = (project: Project) => {
    if (project.status === "draft") {
      navigate(`/projects/${project.id}/wizard`);
    } else {
      navigate(`/projects/${project.id}`);
    }
  };

  if (loading) {
    return (
      <div className={styles.spinnerContainer}>
        <Spinner size="large" label="Loading dashboard..." />
      </div>
    );
  }

  const deployingCount = stats?.by_status?.deploying ?? 0;
  const deployedCount = stats?.by_status?.deployed ?? 0;

  const donutData = stats
    ? Object.entries(stats.by_status)
        .filter(([, count]) => count > 0)
        .map(([status, count]) => ({
          legend: STATUS_LABELS[status] ?? status,
          data: count,
          color: STATUS_COLORS[status] ?? "#888888",
        }))
    : [];

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <Title1>Project Dashboard</Title1>
        <div className={styles.headerActions}>
          <Button
            icon={<ArrowClockwiseRegular />}
            appearance="subtle"
            onClick={loadData}
          >
            Refresh
          </Button>
          <Dialog open={dialogOpen} onOpenChange={(_e, data) => setDialogOpen(data.open)}>
            <DialogTrigger disableButtonEnhancement>
              <Button icon={<AddRegular />} appearance="primary">
                New Project
              </Button>
            </DialogTrigger>
            <DialogSurface>
              <DialogTitle>Create New Project</DialogTitle>
              <DialogBody>
                <Field
                  label="Project Name"
                  required
                  className={styles.dialogField}
                >
                  <Input
                    value={newName}
                    onChange={(_e, data) => setNewName(data.value)}
                    placeholder="My Landing Zone"
                  />
                </Field>
                <Field label="Description" className={styles.dialogField}>
                  <Textarea
                    value={newDescription}
                    onChange={(_e, data) => setNewDescription(data.value)}
                    placeholder="Optional project description"
                    rows={3}
                  />
                </Field>
              </DialogBody>
              <DialogActions>
                <DialogTrigger disableButtonEnhancement>
                  <Button appearance="secondary">Cancel</Button>
                </DialogTrigger>
                <Button
                  appearance="primary"
                  onClick={handleCreate}
                  disabled={!newName.trim() || creating}
                >
                  {creating ? "Creating..." : "Create"}
                </Button>
              </DialogActions>
            </DialogSurface>
          </Dialog>
        </div>
      </div>

      {/* Summary Cards */}
      <div className={styles.cardsRow}>
        <Card className={styles.statCard}>
          <CardHeader header={<Subtitle2>Total Projects</Subtitle2>} />
          <Title1 className={styles.statValue}>{stats?.total ?? 0}</Title1>
        </Card>
        <Card className={styles.statCard}>
          <CardHeader header={<Subtitle2>Active</Subtitle2>} />
          <Title1 className={styles.statValue}>{deployingCount}</Title1>
        </Card>
        <Card className={styles.statCard}>
          <CardHeader header={<Subtitle2>Deployed</Subtitle2>} />
          <Title1 className={styles.statValue}>{deployedCount}</Title1>
        </Card>
        <Card className={styles.statCard}>
          <CardHeader header={<Subtitle2>Avg Compliance Score</Subtitle2>} />
          <Title1 className={styles.statValue}>
            {stats?.avg_compliance_score != null
              ? `${Math.round(stats.avg_compliance_score)}%`
              : "—"}
          </Title1>
        </Card>
      </div>

      {/* Charts Row */}
      <div className={styles.chartsRow}>
        <Card className={styles.chartCard}>
          <CardHeader header={<Title2>Status Distribution</Title2>} />
          {donutData.length > 0 ? (
            <DonutChart
              data={{ chartData: donutData }}
              innerRadius={55}
              width={300}
              height={250}
            />
          ) : (
            <div className={styles.emptyState}>
              <Body1>No project data to display</Body1>
            </div>
          )}
        </Card>
        <Card className={styles.chartCard}>
          <CardHeader header={<Title2>Compliance Scores</Title2>} />
          <div className={styles.emptyState}>
            <Body1>Compliance data will appear after scoring</Body1>
          </div>
        </Card>
      </div>

      {/* Project Table */}
      {projects.length === 0 ? (
        <Card>
          <div className={styles.emptyState}>
            <Title2>No projects yet</Title2>
            <Body1>Create your first project to get started.</Body1>
          </div>
        </Card>
      ) : (
        <Table aria-label="Projects">
          <TableHeader>
            <TableRow>
              <TableHeaderCell>Name</TableHeaderCell>
              <TableHeaderCell>Status</TableHeaderCell>
              <TableHeaderCell>Created</TableHeaderCell>
              <TableHeaderCell>Actions</TableHeaderCell>
            </TableRow>
          </TableHeader>
          <TableBody>
            {projects.map((project) => (
              <TableRow key={project.id}>
                <TableCell>{project.name}</TableCell>
                <TableCell>
                  <Badge
                    appearance="filled"
                    color={getStatusBadgeColor(project.status)}
                  >
                    {STATUS_LABELS[project.status] ?? project.status}
                  </Badge>
                </TableCell>
                <TableCell>
                  {new Date(project.created_at).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  <Button
                    icon={
                      project.status === "draft" ? (
                        <PlayRegular />
                      ) : (
                        <EyeRegular />
                      )
                    }
                    appearance="subtle"
                    size="small"
                    onClick={() => handleNavigate(project)}
                    aria-label={
                      project.status === "draft" ? "Continue" : "View"
                    }
                  >
                    {project.status === "draft" ? "Continue" : "View"}
                  </Button>
                  <Button
                    icon={<DeleteRegular />}
                    appearance="subtle"
                    size="small"
                    onClick={() => handleDelete(project.id)}
                    aria-label="Delete"
                  >
                    Delete
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
