import {
  Badge,
  Button,
  MessageBar,
  MessageBarBody,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHeaderCell,
  TableRow,
  Text,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import { DeleteRegular, EditRegular } from "@fluentui/react-icons";
import type { WorkloadRecord } from "../services/api";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface WorkloadInventoryTabProps {
  workloads: WorkloadRecord[];
  listLoading: boolean;
  listError: string | null;
  onRefresh: () => void;
  onOpenCreate: () => void;
  onOpenEdit: (wl: WorkloadRecord) => void;
  onDeleteTarget: (wl: WorkloadRecord) => void;
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const useStyles = makeStyles({
  tabContent: {
    paddingTop: tokens.spacingVerticalL,
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalM,
  },
  actionRow: {
    display: "flex",
    gap: tokens.spacingHorizontalM,
    alignItems: "center",
    justifyContent: "space-between",
  },
  buttonRow: {
    display: "flex",
    gap: tokens.spacingHorizontalS,
  },
  tableWrapper: {
    overflowX: "auto",
  },
  actionCellButtons: {
    display: "flex",
    gap: tokens.spacingHorizontalXS,
  },
});

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function WorkloadInventoryTab({
  workloads,
  listLoading,
  listError,
  onRefresh,
  onOpenCreate,
  onOpenEdit,
  onDeleteTarget,
}: WorkloadInventoryTabProps) {
  const styles = useStyles();

  return (
    <div className={styles.tabContent}>
      <div className={styles.actionRow}>
        <Text>
          {workloads.length} workload{workloads.length !== 1 ? "s" : ""} in this project
        </Text>
        <div className={styles.buttonRow}>
          <Button appearance="subtle" onClick={onRefresh} disabled={listLoading}>
            {listLoading ? <Spinner size="tiny" /> : "Refresh"}
          </Button>
          <Button appearance="primary" onClick={onOpenCreate}>
            Add Workload
          </Button>
        </div>
      </div>

      {listError && (
        <MessageBar intent="error">
          <MessageBarBody>{listError}</MessageBarBody>
        </MessageBar>
      )}
      {listLoading && <Spinner label="Loading workloads\u2026" />}
      {!listLoading && workloads.length === 0 && (
        <MessageBar intent="info">
          <MessageBarBody>
            No workloads yet. Import a file or add one manually.
          </MessageBarBody>
        </MessageBar>
      )}
      {!listLoading && workloads.length > 0 && (
        <div className={styles.tableWrapper}>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHeaderCell>Name</TableHeaderCell>
                <TableHeaderCell>Type</TableHeaderCell>
                <TableHeaderCell>Platform</TableHeaderCell>
                <TableHeaderCell>CPUs</TableHeaderCell>
                <TableHeaderCell>RAM (GB)</TableHeaderCell>
                <TableHeaderCell>OS</TableHeaderCell>
                <TableHeaderCell>Criticality</TableHeaderCell>
                <TableHeaderCell>Strategy</TableHeaderCell>
                <TableHeaderCell>Actions</TableHeaderCell>
              </TableRow>
            </TableHeader>
            <TableBody>
              {workloads.map((wl) => (
                <TableRow key={wl.id}>
                  <TableCell>{wl.name}</TableCell>
                  <TableCell>{wl.type}</TableCell>
                  <TableCell>{wl.source_platform}</TableCell>
                  <TableCell>{wl.cpu_cores ?? "\u2014"}</TableCell>
                  <TableCell>{wl.memory_gb ?? "\u2014"}</TableCell>
                  <TableCell>{wl.os_type ?? "\u2014"}</TableCell>
                  <TableCell>
                    <Badge
                      appearance="tint"
                      color={
                        wl.criticality === "mission-critical"
                          ? "danger"
                          : wl.criticality === "business-critical"
                            ? "warning"
                            : "informative"
                      }
                    >
                      {wl.criticality}
                    </Badge>
                  </TableCell>
                  <TableCell>{wl.migration_strategy}</TableCell>
                  <TableCell>
                    <div className={styles.actionCellButtons}>
                      <Button
                        appearance="subtle"
                        size="small"
                        icon={<EditRegular />}
                        onClick={() => onOpenEdit(wl)}
                        aria-label={`Edit ${wl.name}`}
                      />
                      <Button
                        appearance="subtle"
                        size="small"
                        icon={<DeleteRegular />}
                        onClick={() => onDeleteTarget(wl)}
                        aria-label={`Delete ${wl.name}`}
                      />
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
