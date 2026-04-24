import { useState, useEffect, useCallback } from "react";
import {
  Body1,
  Body2,
  Card,
  Subtitle2,
  Badge,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHeaderCell,
  TableRow,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import { api } from "../../services/api";

interface AuditEntryData {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  resource: string;
  details: string;
  severity: string;
}

interface AuditListData {
  entries: AuditEntryData[];
  total_count: number;
}

type EventColor = "informative" | "warning" | "danger" | "success";

function eventBadgeColor(action: string): EventColor {
  if (action.includes("drift")) return "warning";
  if (action.includes("error") || action.includes("fail")) return "danger";
  if (action.includes("deploy") || action.includes("success")) return "success";
  return "informative";
}

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalL,
  },
  tableCard: {
    paddingTop: tokens.spacingVerticalL,
    paddingBottom: tokens.spacingVerticalL,
    paddingLeft: tokens.spacingHorizontalL,
    paddingRight: tokens.spacingHorizontalL,
  },
  headerRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: tokens.spacingVerticalM,
  },
  truncated: {
    maxWidth: "200px",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  spinnerContainer: {
    display: "flex",
    justifyContent: "center",
    paddingTop: tokens.spacingVerticalXXL,
    paddingBottom: tokens.spacingVerticalXXL,
  },
  errorText: {
    color: tokens.colorPaletteRedForeground1,
  },
  emptyState: {
    paddingTop: tokens.spacingVerticalL,
    paddingBottom: tokens.spacingVerticalL,
    textAlign: "center",
    color: tokens.colorNeutralForeground3,
  },
});

interface AuditPanelProps {
  projectId: string;
}

export default function AuditPanel({ projectId }: AuditPanelProps) {
  const styles = useStyles();
  const [auditData, setAuditData] = useState<AuditListData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.governance.audit.list(projectId) as unknown;
      setAuditData(data as AuditListData);
    } catch {
      setError("Failed to load audit trail.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <div className={styles.spinnerContainer}>
        <Spinner size="medium" label="Loading audit trail..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <Body1 className={styles.errorText}>{error}</Body1>
      </div>
    );
  }

  const entries = auditData?.entries ?? [];
  const total = auditData?.total_count ?? 0;

  return (
    <div className={styles.container}>
      <Card className={styles.tableCard}>
        <div className={styles.headerRow}>
          <Subtitle2>Audit Trail ({total} entries)</Subtitle2>
        </div>

        {entries.length > 0 ? (
          <>
            <Body2>{new Date(entries[0].timestamp).toLocaleDateString()}</Body2>
            <Table aria-label="Governance audit trail">
              <TableHeader>
                <TableRow>
                  <TableHeaderCell>Action</TableHeaderCell>
                  <TableHeaderCell>Actor</TableHeaderCell>
                  <TableHeaderCell>Resource</TableHeaderCell>
                  <TableHeaderCell>Details</TableHeaderCell>
                  <TableHeaderCell>Time</TableHeaderCell>
                </TableRow>
              </TableHeader>
              <TableBody>
                {entries.map((entry: AuditEntryData) => (
                  <TableRow key={entry.id}>
                    <TableCell>
                      <Badge appearance="filled" color={eventBadgeColor(entry.action)}>
                        {entry.action}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Body2>{entry.actor}</Body2>
                    </TableCell>
                    <TableCell>
                      <Body2 className={styles.truncated} title={entry.resource}>
                        {entry.resource}
                      </Body2>
                    </TableCell>
                    <TableCell>
                      <Body2>{entry.details}</Body2>
                    </TableCell>
                    <TableCell>
                      <Body2>{new Date(entry.timestamp).toLocaleTimeString()}</Body2>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </>
        ) : (
          <Body1 className={styles.emptyState}>No audit entries found.</Body1>
        )}
      </Card>
    </div>
  );
}
