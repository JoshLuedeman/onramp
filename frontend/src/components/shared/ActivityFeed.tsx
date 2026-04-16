import { useCallback, useEffect, useState } from "react";
import {
  Card,
  Text,
  Avatar,
  Spinner,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import { HistoryRegular } from "@fluentui/react-icons";
import { api } from "../../services/api";
import type { ActivityEntryItem } from "../../services/api";

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
    padding: tokens.spacingVerticalM,
  },
  title: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase400,
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
    marginBottom: tokens.spacingVerticalS,
  },
  timeline: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXS,
  },
  entry: {
    display: "flex",
    alignItems: "flex-start",
    gap: tokens.spacingHorizontalS,
    padding: tokens.spacingVerticalXS,
  },
  entryContent: {
    display: "flex",
    flexDirection: "column",
    flex: 1,
  },
  description: {
    fontSize: tokens.fontSizeBase200,
  },
  timestamp: {
    fontSize: tokens.fontSizeBase100,
    color: tokens.colorNeutralForeground3,
  },
  emptyState: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: tokens.spacingVerticalXXL,
    color: tokens.colorNeutralForeground3,
    gap: tokens.spacingVerticalS,
  },
  loading: {
    display: "flex",
    justifyContent: "center",
    padding: tokens.spacingVerticalL,
  },
});

interface ActivityFeedProps {
  projectId: string;
}

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString();
}

export default function ActivityFeed({ projectId }: ActivityFeedProps) {
  const styles = useStyles();
  const [activities, setActivities] = useState<ActivityEntryItem[]>(
    [],
  );
  const [loading, setLoading] = useState(true);

  const loadActivities = useCallback(async () => {
    setLoading(true);
    try {
      const result = await api.collaboration.getActivity(projectId);
      setActivities(result.activities);
    } catch {
      // Silently handle — empty state shown
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadActivities();
  }, [loadActivities]);

  if (loading) {
    return (
      <div className={styles.loading}>
        <Spinner size="small" label="Loading activity…" />
      </div>
    );
  }

  return (
    <Card className={styles.container} data-testid="activity-feed">
      <Text className={styles.title}>
        <HistoryRegular />
        Activity Feed
      </Text>

      {activities.length === 0 ? (
        <div className={styles.emptyState}>
          <HistoryRegular />
          <Text>No activity yet</Text>
        </div>
      ) : (
        <div className={styles.timeline}>
          {activities.map((entry, index) => (
            <div
              key={`${entry.user_id}-${entry.timestamp}-${index}`}
              className={styles.entry}
            >
              <Avatar name={entry.user_id} size={24} />
              <div className={styles.entryContent}>
                <Text className={styles.description}>
                  {entry.description}
                </Text>
                <Text className={styles.timestamp}>
                  {formatTimestamp(entry.timestamp)}
                </Text>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
