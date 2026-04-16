import {
  makeStyles,
  tokens,
  Card,
  Text,
  Subtitle2,
} from "@fluentui/react-components";
import {
  ShieldCheckmarkRegular,
  MoneyRegular,
  CloudRegular,
  ServerRegular,
  LockClosedRegular,
  ArrowSyncRegular,
} from "@fluentui/react-icons";

export interface SuggestedPromptsProps {
  onSelect: (prompt: string) => void;
}

interface PromptCard {
  text: string;
  icon: React.ReactNode;
  description: string;
}

const PROMPTS: PromptCard[] = [
  {
    text: "Add disaster recovery",
    icon: <ArrowSyncRegular />,
    description: "Design a DR strategy with failover regions and RTO/RPO targets",
  },
  {
    text: "Optimize for cost",
    icon: <MoneyRegular />,
    description: "Review architecture for cost savings and right-sizing opportunities",
  },
  {
    text: "Add HIPAA compliance",
    icon: <ShieldCheckmarkRegular />,
    description: "Add HIPAA controls, encryption, audit logging, and BAA requirements",
  },
  {
    text: "Compare hub-spoke vs mesh",
    icon: <CloudRegular />,
    description: "Evaluate network topologies for your organization's requirements",
  },
  {
    text: "Right-size my VMs",
    icon: <ServerRegular />,
    description: "Analyze compute needs and recommend optimal VM SKUs",
  },
  {
    text: "Add security controls",
    icon: <LockClosedRegular />,
    description: "Implement defense-in-depth with Azure Firewall, WAF, and Defender",
  },
];

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: tokens.spacingVerticalL,
    padding: tokens.spacingVerticalXXL,
  },
  title: {
    textAlign: "center",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
    gap: tokens.spacingHorizontalM,
    width: "100%",
    maxWidth: "800px",
  },
  card: {
    cursor: "pointer",
    padding: tokens.spacingVerticalM,
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
    ":hover": {
      backgroundColor: tokens.colorNeutralBackground1Hover,
    },
  },
  cardHeader: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
  },
  icon: {
    color: tokens.colorBrandForeground1,
    fontSize: tokens.fontSizeBase400,
  },
  description: {
    color: tokens.colorNeutralForeground3,
    fontSize: tokens.fontSizeBase200,
  },
});

export default function SuggestedPrompts({ onSelect }: SuggestedPromptsProps) {
  const styles = useStyles();

  return (
    <div className={styles.container} data-testid="suggested-prompts">
      <Subtitle2 className={styles.title}>
        What would you like to explore?
      </Subtitle2>
      <div className={styles.grid}>
        {PROMPTS.map((prompt) => (
          <Card
            key={prompt.text}
            className={styles.card}
            onClick={() => onSelect(prompt.text)}
            role="button"
            aria-label={prompt.text}
          >
            <div className={styles.cardHeader}>
              <span className={styles.icon}>{prompt.icon}</span>
              <Text weight="semibold">{prompt.text}</Text>
            </div>
            <Text className={styles.description}>{prompt.description}</Text>
          </Card>
        ))}
      </div>
    </div>
  );
}
