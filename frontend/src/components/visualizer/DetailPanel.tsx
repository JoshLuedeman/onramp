import {
  Card,
  Text,
  Divider,
  Badge,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import { DismissRegular } from "@fluentui/react-icons";

const useStyles = makeStyles({
  panel: {
    padding: "16px",
    minWidth: "320px",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "12px",
  },
  title: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase400,
  },
  section: {
    marginTop: "12px",
  },
  sectionTitle: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase300,
    marginBottom: "4px",
  },
  propertyRow: {
    display: "flex",
    justifyContent: "space-between",
    padding: "4px 0",
  },
  label: {
    color: tokens.colorNeutralForeground3,
  },
  clickableIcon: {
    cursor: "pointer",
  },
  divider: {
    marginTop: tokens.spacingVerticalM,
    marginBottom: tokens.spacingVerticalM,
  },
});

interface DetailPanelProps {
  component: {
    type: string;
    name: string;
    properties?: Record<string, unknown>;
    tags?: Record<string, string>;
  };
  onClose: () => void;
}

export default function DetailPanel({ component, onClose }: DetailPanelProps) {
  const styles = useStyles();

  return (
    <Card className={styles.panel}>
      <div className={styles.header}>
        <Text className={styles.title}>{component.name}</Text>
        <DismissRegular
          className={styles.clickableIcon}
          onClick={onClose}
        />
      </div>
      <Badge appearance="outline">{component.type}</Badge>
      <Divider className={styles.divider} />

      {component.properties && (
        <div className={styles.section}>
          <Text className={styles.sectionTitle}>Properties</Text>
          {Object.entries(component.properties).map(([key, value]) => (
            <div key={key} className={styles.propertyRow}>
              <Text className={styles.label}>{key}</Text>
              <Text>{String(value)}</Text>
            </div>
          ))}
        </div>
      )}

      {component.tags && Object.keys(component.tags).length > 0 && (
        <div className={styles.section}>
          <Text className={styles.sectionTitle}>Tags</Text>
          {Object.entries(component.tags).map(([key, value]) => (
            <div key={key} className={styles.propertyRow}>
              <Text className={styles.label}>{key}</Text>
              <Text>{value}</Text>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
