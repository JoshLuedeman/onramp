import { useState, useCallback, useMemo } from "react";
import {
  Tree,
  TreeItem,
  TreeItemLayout,
  TreeOpenChangeData,
  makeStyles,
  tokens,
  Badge,
  Text,
  Card,
  CardHeader,
  Button,
  Divider,
} from "@fluentui/react-components";
import {
  OrganizationRegular,
  ServerRegular,
  BuildingRegular,
  BeakerRegular,
  ArchiveRegular,
  CloudRegular,
  ExpandUpLeftRegular,
  ArrowCollapseAllRegular,
} from "@fluentui/react-icons";

type GroupType = "root" | "platform" | "landingZone" | "sandbox" | "decommissioned" | "default";

const PLATFORM_KEYWORDS = ["identity", "management", "connectivity"];
const LANDING_ZONE_KEYWORDS = ["corp", "online", "confidential", "landing"];
const SANDBOX_KEYWORDS = ["sandbox"];
const DECOMMISSIONED_KEYWORDS = ["decommissioned"];

function classifyGroup(key: string, isTopLevel: boolean): GroupType {
  const lower = key.toLowerCase();
  if (isTopLevel) return "root";
  if (DECOMMISSIONED_KEYWORDS.some((kw) => lower.includes(kw))) return "decommissioned";
  if (SANDBOX_KEYWORDS.some((kw) => lower.includes(kw))) return "sandbox";
  if (PLATFORM_KEYWORDS.some((kw) => lower.includes(kw))) return "platform";
  if (LANDING_ZONE_KEYWORDS.some((kw) => lower.includes(kw))) return "landingZone";
  return "default";
}

const GROUP_TYPE_LABELS: Record<GroupType, string> = {
  root: "Root",
  platform: "Platform",
  landingZone: "Landing Zone",
  sandbox: "Sandbox",
  decommissioned: "Decommissioned",
  default: "Management Group",
};

const GROUP_ICONS: Record<GroupType, React.ElementType> = {
  root: OrganizationRegular,
  platform: ServerRegular,
  landingZone: BuildingRegular,
  sandbox: BeakerRegular,
  decommissioned: ArchiveRegular,
  default: OrganizationRegular,
};

const useStyles = makeStyles({
  container: {
    padding: "24px",
  },
  toolbar: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    marginBottom: "12px",
    maxWidth: "600px",
  },
  tree: {
    maxWidth: "600px",
  },
  iconRoot: { color: tokens.colorPaletteBlueForeground2 },
  iconPlatform: { color: tokens.colorPaletteGreenForeground2 },
  iconLandingZone: { color: tokens.colorPalettePurpleForeground2 },
  iconSandbox: { color: tokens.colorPaletteYellowForeground2 },
  iconDecommissioned: { color: tokens.colorPaletteYellowForeground2 },
  iconDefault: { color: tokens.colorPaletteBlueForeground2 },
  iconSubscription: { color: tokens.colorNeutralForeground2 },
  groupName: { fontWeight: tokens.fontWeightSemibold },
  detailPanel: {
    marginTop: "16px",
    padding: "16px",
    maxWidth: "600px",
  },
  detailHeader: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  detailTitle: {
    fontWeight: tokens.fontWeightSemibold,
  },
  detailMeta: {
    display: "flex",
    gap: "16px",
    marginTop: "8px",
    marginBottom: "8px",
  },
  subList: {
    listStyleType: "none",
    padding: 0,
    margin: 0,
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  subItem: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
  },
});

const ICON_STYLE_MAP: Record<GroupType, string> = {
  root: "iconRoot",
  platform: "iconPlatform",
  landingZone: "iconLandingZone",
  sandbox: "iconSandbox",
  decommissioned: "iconDecommissioned",
  default: "iconDefault",
};

interface ManagementGroup {
  display_name?: string;
  displayName?: string;
  children?: Record<string, ManagementGroup>;
}

interface ArchitectureDiagramProps {
  managementGroups: Record<string, ManagementGroup>;
  subscriptions?: { name: string; purpose: string; management_group: string; budget?: number }[];
}

function collectAllKeys(groups: Record<string, ManagementGroup>): string[] {
  const keys: string[] = [];
  const walk = (g: Record<string, ManagementGroup>) => {
    for (const [k, v] of Object.entries(g)) {
      keys.push(k);
      if (v.children) walk(v.children);
    }
  };
  walk(groups);
  return keys;
}

export default function ArchitectureDiagram({
  managementGroups,
  subscriptions = [],
}: ArchitectureDiagramProps) {
  const styles = useStyles();
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const allKeys = useMemo(() => collectAllKeys(managementGroups), [managementGroups]);
  const [openItems, setOpenItems] = useState<Set<string>>(new Set(allKeys));
  const [allExpanded, setAllExpanded] = useState(true);

  const handleOpenChange = useCallback(
    (_e: unknown, data: TreeOpenChangeData) => {
      setOpenItems(new Set(data.openItems as Iterable<string>));
    },
    [],
  );

  const toggleExpandAll = useCallback(() => {
    if (allExpanded) {
      setOpenItems(new Set());
    } else {
      setOpenItems(new Set(allKeys));
    }
    setAllExpanded((prev) => !prev);
  }, [allExpanded, allKeys]);

  const getSubsForGroup = (groupKey: string) =>
    subscriptions.filter((s) => s.management_group === groupKey);

  const renderGroup = (
    key: string,
    group: ManagementGroup,
    isTopLevel: boolean,
  ): React.ReactNode => {
    const name = group.display_name || group.displayName || key;
    const subs = getSubsForGroup(key);
    const groupType = classifyGroup(key, isTopLevel);
    const Icon = GROUP_ICONS[groupType];
    const iconStyleKey = ICON_STYLE_MAP[groupType] as keyof typeof styles;

    return (
      <TreeItem key={key} itemType="branch" value={key}>
        <TreeItemLayout
          iconBefore={<Icon className={styles[iconStyleKey]} />}
          onClick={() => setSelectedNode(key)}
        >
          <span className={styles.groupName}>{name}</span>
          {subs.length > 0 && (
            <Badge appearance="tint" size="small" style={{ marginLeft: 8 }}>
              {subs.length} sub{subs.length !== 1 ? "s" : ""}
            </Badge>
          )}
        </TreeItemLayout>
        {subs.map((sub) => (
          <TreeItem key={sub.name} itemType="leaf">
            <TreeItemLayout
              iconBefore={<CloudRegular className={styles.iconSubscription} />}
            >
              {sub.name}
            </TreeItemLayout>
          </TreeItem>
        ))}
        {group.children &&
          Object.entries(group.children).map(([childKey, childGroup]) =>
            renderGroup(childKey, childGroup, false),
          )}
      </TreeItem>
    );
  };

  const selectedSubs = selectedNode ? getSubsForGroup(selectedNode) : [];
  const selectedGroupType = selectedNode
    ? classifyGroup(
        selectedNode,
        Object.keys(managementGroups).includes(selectedNode),
      )
    : "default";
  const SelectedIcon = GROUP_ICONS[selectedGroupType];
  const selectedIconStyle = ICON_STYLE_MAP[selectedGroupType] as keyof typeof styles;

  const budgetTotal = selectedSubs.reduce(
    (sum, s) => sum + (s.budget ?? 0),
    0,
  );

  return (
    <div className={styles.container}>
      <div className={styles.toolbar}>
        <Button
          size="small"
          icon={allExpanded ? <ArrowCollapseAllRegular /> : <ExpandUpLeftRegular />}
          appearance="subtle"
          onClick={toggleExpandAll}
        >
          {allExpanded ? "Collapse All" : "Expand All"}
        </Button>
      </div>

      <Tree
        className={styles.tree}
        aria-label="Management Group Hierarchy"
        openItems={openItems}
        onOpenChange={handleOpenChange}
      >
        {Object.entries(managementGroups).map(([key, group]) =>
          renderGroup(key, group, true),
        )}
      </Tree>

      {selectedNode && (
        <Card className={styles.detailPanel}>
          <CardHeader
            image={<SelectedIcon className={styles[selectedIconStyle]} />}
            header={
              <Text className={styles.detailTitle}>
                {managementGroups[selectedNode]?.display_name ||
                  managementGroups[selectedNode]?.displayName ||
                  selectedNode}
              </Text>
            }
            description={
              <Badge appearance="outline" size="small">
                {GROUP_TYPE_LABELS[selectedGroupType]}
              </Badge>
            }
          />
          <Divider />
          <div className={styles.detailMeta}>
            <Text>
              <strong>Subscriptions:</strong> {selectedSubs.length}
            </Text>
            {budgetTotal > 0 && (
              <Text>
                <strong>Total Budget:</strong> ${budgetTotal.toLocaleString()}
              </Text>
            )}
          </div>
          {selectedSubs.length > 0 ? (
            <ul className={styles.subList}>
              {selectedSubs.map((sub) => (
                <li key={sub.name} className={styles.subItem}>
                  <CloudRegular className={styles.iconSubscription} />
                  <Text>
                    <strong>{sub.name}</strong> — {sub.purpose}
                    {sub.budget != null && (
                      <> (${sub.budget.toLocaleString()})</>
                    )}
                  </Text>
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
