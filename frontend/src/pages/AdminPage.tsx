import { useState, useEffect, useCallback } from "react";
import {
  Title1,
  Body1,
  Badge,
  Table,
  TableHeader,
  TableRow,
  TableHeaderCell,
  TableBody,
  TableCell,
  Spinner,
  Card,
  Button,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import { ArrowClockwiseRegular } from "@fluentui/react-icons";
import { api } from "../services/api";
import type { PluginResponse } from "../services/api";

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
  spinnerContainer: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    minHeight: "400px",
  },
  emptyState: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: tokens.spacingVerticalXXXL,
    gap: tokens.spacingVerticalM,
  },
  errorText: {
    color: tokens.colorPaletteRedForeground1,
  },
});

type BadgeColor = "success" | "danger";

function statusBadgeColor(enabled: boolean): BadgeColor {
  return enabled ? "success" : "danger";
}

function typeBadgeLabel(pluginType: string): string {
  switch (pluginType) {
    case "compliance":
      return "Compliance";
    case "architecture":
      return "Architecture";
    case "output":
      return "Output Format";
    default:
      return pluginType;
  }
}

export default function AdminPage() {
  const styles = useStyles();
  const [plugins, setPlugins] = useState<PluginResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPlugins = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.plugins.list();
      setPlugins(response.plugins);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load plugins");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPlugins();
  }, [loadPlugins]);

  if (loading) {
    return (
      <div className={styles.spinnerContainer}>
        <Spinner size="large" label="Loading plugins..." />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Title1>Plugin Management</Title1>
        <Button
          icon={<ArrowClockwiseRegular />}
          appearance="subtle"
          onClick={loadPlugins}
        >
          Refresh
        </Button>
      </div>

      {error && (
        <Body1 className={styles.errorText}>{error}</Body1>
      )}

      {plugins.length === 0 && !error ? (
        <Card>
          <div className={styles.emptyState}>
            <Title1>No plugins installed</Title1>
            <Body1>
              Install plugins to extend OnRamp with custom compliance frameworks,
              architecture patterns, and output formats.
            </Body1>
          </div>
        </Card>
      ) : plugins.length > 0 ? (
        <Table aria-label="Installed plugins">
          <TableHeader>
            <TableRow>
              <TableHeaderCell>Name</TableHeaderCell>
              <TableHeaderCell>Version</TableHeaderCell>
              <TableHeaderCell>Type</TableHeaderCell>
              <TableHeaderCell>Description</TableHeaderCell>
              <TableHeaderCell>Status</TableHeaderCell>
            </TableRow>
          </TableHeader>
          <TableBody>
            {plugins.map((plugin) => (
              <TableRow key={`${plugin.plugin_type}-${plugin.name}`}>
                <TableCell>{plugin.name}</TableCell>
                <TableCell>{plugin.version}</TableCell>
                <TableCell>
                  <Badge appearance="outline">
                    {typeBadgeLabel(plugin.plugin_type)}
                  </Badge>
                </TableCell>
                <TableCell>{plugin.description}</TableCell>
                <TableCell>
                  <Badge
                    appearance="filled"
                    color={statusBadgeColor(plugin.enabled)}
                  >
                    {plugin.enabled ? "Enabled" : "Disabled"}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : null}
    </div>
  );
}
