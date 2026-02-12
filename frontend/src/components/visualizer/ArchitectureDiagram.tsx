import { useState } from "react";
import {
  Tree,
  TreeItem,
  TreeItemLayout,
  makeStyles,
  tokens,
  Badge,
  Text,
  Card,
} from "@fluentui/react-components";
import {
  FolderRegular,
  CloudRegular,
} from "@fluentui/react-icons";

const useStyles = makeStyles({
  container: {
    padding: "24px",
  },
  tree: {
    maxWidth: "600px",
  },
  detailPanel: {
    marginTop: "16px",
    padding: "16px",
    maxWidth: "600px",
  },
  detailTitle: {
    fontWeight: tokens.fontWeightSemibold,
    marginBottom: "8px",
  },
});

interface ManagementGroup {
  display_name?: string;
  displayName?: string;
  children?: Record<string, ManagementGroup>;
}

interface ArchitectureDiagramProps {
  managementGroups: Record<string, ManagementGroup>;
  subscriptions?: { name: string; purpose: string; management_group: string }[];
}

export default function ArchitectureDiagram({
  managementGroups,
  subscriptions = [],
}: ArchitectureDiagramProps) {
  const styles = useStyles();
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const getSubsForGroup = (groupKey: string) =>
    subscriptions.filter((s) => s.management_group === groupKey);

  const renderGroup = (key: string, group: ManagementGroup): React.ReactNode => {
    const name = group.display_name || group.displayName || key;
    const subs = getSubsForGroup(key);

    return (
      <TreeItem key={key} itemType="branch" value={key}>
        <TreeItemLayout
          iconBefore={<FolderRegular />}
          onClick={() => setSelectedNode(key)}
        >
          {name}
          {subs.length > 0 && (
            <Badge appearance="tint" size="small" style={{ marginLeft: 8 }}>
              {subs.length} sub{subs.length > 1 ? "s" : ""}
            </Badge>
          )}
        </TreeItemLayout>
        {subs.map((sub) => (
          <TreeItem key={sub.name} itemType="leaf">
            <TreeItemLayout iconBefore={<CloudRegular />}>
              {sub.name}
            </TreeItemLayout>
          </TreeItem>
        ))}
        {group.children &&
          Object.entries(group.children).map(([childKey, childGroup]) =>
            renderGroup(childKey, childGroup)
          )}
      </TreeItem>
    );
  };

  const selectedSubs = selectedNode ? getSubsForGroup(selectedNode) : [];

  return (
    <div className={styles.container}>
      <Tree className={styles.tree} aria-label="Management Group Hierarchy">
        {Object.entries(managementGroups).map(([key, group]) =>
          renderGroup(key, group)
        )}
      </Tree>

      {selectedNode && (
        <Card className={styles.detailPanel}>
          <Text className={styles.detailTitle}>
            <FolderRegular /> {selectedNode}
          </Text>
          {selectedSubs.length > 0 ? (
            <ul>
              {selectedSubs.map((sub) => (
                <li key={sub.name}>
                  <strong>{sub.name}</strong> — {sub.purpose}
                </li>
              ))}
            </ul>
          ) : (
            <Text>No subscriptions directly in this management group.</Text>
          )}
        </Card>
      )}
    </div>
  );
}
