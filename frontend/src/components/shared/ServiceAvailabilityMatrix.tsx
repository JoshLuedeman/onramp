import { useState, useMemo } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHeaderCell,
  TableRow,
  Text,
  Badge,
  makeStyles,
  tokens,
  Input,
} from "@fluentui/react-components";
import {
  CheckmarkCircleRegular,
  DismissCircleRegular,
  WarningRegular,
} from "@fluentui/react-icons";
import type { ServiceAvailabilityItem } from "../../services/api";

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalM,
  },
  searchBar: {
    maxWidth: "320px",
  },
  table: {
    width: "100%",
  },
  available: {
    color: tokens.colorPaletteGreenForeground1,
  },
  unavailable: {
    color: tokens.colorPaletteRedForeground1,
  },
  limited: {
    color: tokens.colorPaletteYellowForeground1,
  },
  highlighted: {
    backgroundColor: tokens.colorNeutralBackground1Selected,
  },
  usedService: {
    fontWeight: tokens.fontWeightSemibold,
  },
  notesCell: {
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
  },
  categoryBadge: {
    marginRight: tokens.spacingHorizontalXS,
  },
  sortableHeader: {
    cursor: "pointer",
  },
});

export interface ServiceAvailabilityMatrixProps {
  services: ServiceAvailabilityItem[];
  targetEnvironment?: string;
  architecture?: { services?: string[] };
}

type SortColumn = "service_name" | "category" | "commercial" | "government" | "china";

export default function ServiceAvailabilityMatrix({
  services,
  targetEnvironment,
  architecture,
}: ServiceAvailabilityMatrixProps) {
  const styles = useStyles();
  const [filter, setFilter] = useState("");
  const [sortColumn, setSortColumn] = useState<SortColumn>("service_name");
  const [sortAsc, setSortAsc] = useState(true);

  const architectureServices = useMemo(
    () => new Set((architecture?.services ?? []).map((s) => s.toLowerCase())),
    [architecture],
  );

  const filtered = useMemo(() => {
    const term = filter.toLowerCase();
    let result = services.filter(
      (s) =>
        s.service_name.toLowerCase().includes(term) ||
        s.category.toLowerCase().includes(term),
    );

    result = [...result].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];
      if (typeof aVal === "boolean" && typeof bVal === "boolean") {
        return sortAsc ? Number(bVal) - Number(aVal) : Number(aVal) - Number(bVal);
      }
      const cmp = String(aVal).localeCompare(String(bVal));
      return sortAsc ? cmp : -cmp;
    });

    return result;
  }, [services, filter, sortColumn, sortAsc]);

  const handleSort = (col: SortColumn) => {
    if (sortColumn === col) {
      setSortAsc(!sortAsc);
    } else {
      setSortColumn(col);
      setSortAsc(true);
    }
  };

  const renderAvailability = (available: boolean, notes: string) => {
    if (available && notes) {
      return (
        <span className={styles.limited} title={notes}>
          <WarningRegular /> Limited
        </span>
      );
    }
    if (available) {
      return (
        <span className={styles.available}>
          <CheckmarkCircleRegular /> Yes
        </span>
      );
    }
    return (
      <span className={styles.unavailable}>
        <DismissCircleRegular /> No
      </span>
    );
  };

  if (services.length === 0) {
    return <Text>No service availability data available.</Text>;
  }

  return (
    <div className={styles.container}>
      <Input
        className={styles.searchBar}
        placeholder="Filter services…"
        value={filter}
        onChange={(_e, data) => setFilter(data.value)}
        aria-label="Filter services"
      />

      <Table className={styles.table} aria-label="Service Availability Matrix">
        <TableHeader>
          <TableRow>
            <TableHeaderCell
              onClick={() => handleSort("service_name")}
              className={styles.sortableHeader}
            >
              Service Name
            </TableHeaderCell>
            <TableHeaderCell
              onClick={() => handleSort("category")}
              className={styles.sortableHeader}
            >
              Category
            </TableHeaderCell>
            <TableHeaderCell
              className={targetEnvironment === "commercial" ? `${styles.highlighted} ${styles.sortableHeader}` : styles.sortableHeader}
              onClick={() => handleSort("commercial")}
            >
              Commercial
            </TableHeaderCell>
            <TableHeaderCell
              className={targetEnvironment === "government" ? `${styles.highlighted} ${styles.sortableHeader}` : styles.sortableHeader}
              onClick={() => handleSort("government")}
            >
              Government
            </TableHeaderCell>
            <TableHeaderCell
              className={targetEnvironment === "china" ? `${styles.highlighted} ${styles.sortableHeader}` : styles.sortableHeader}
              onClick={() => handleSort("china")}
            >
              China
            </TableHeaderCell>
            <TableHeaderCell>Notes</TableHeaderCell>
          </TableRow>
        </TableHeader>
        <TableBody>
          {filtered.map((svc) => {
            const isUsed = architectureServices.has(svc.service_name.toLowerCase());
            return (
              <TableRow key={svc.service_name}>
                <TableCell className={isUsed ? styles.usedService : undefined}>
                  {svc.service_name}
                </TableCell>
                <TableCell>
                  <Badge
                    className={styles.categoryBadge}
                    appearance="outline"
                    size="small"
                  >
                    {svc.category}
                  </Badge>
                </TableCell>
                <TableCell
                  className={
                    targetEnvironment === "commercial" ? styles.highlighted : undefined
                  }
                >
                  {renderAvailability(svc.commercial, "")}
                </TableCell>
                <TableCell
                  className={
                    targetEnvironment === "government" ? styles.highlighted : undefined
                  }
                >
                  {renderAvailability(svc.government, "")}
                </TableCell>
                <TableCell
                  className={
                    targetEnvironment === "china" ? styles.highlighted : undefined
                  }
                >
                  {renderAvailability(svc.china, "")}
                </TableCell>
                <TableCell className={styles.notesCell}>
                  {svc.notes || "—"}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
