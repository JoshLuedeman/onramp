import { useCallback, useEffect, useState } from "react";
import {
  Button,
  Card,
  Text,
  Textarea,
  Avatar,
  Divider,
  Spinner,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  ChatRegular,
  SendRegular,
  DismissRegular,
} from "@fluentui/react-icons";
import { api } from "../../services/api";
import type { CommentResponseItem } from "../../services/api";

const useStyles = makeStyles({
  panel: {
    display: "flex",
    flexDirection: "column",
    height: "100%",
    minWidth: "320px",
    padding: tokens.spacingVerticalM,
    gap: tokens.spacingVerticalS,
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  title: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase400,
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
  },
  commentList: {
    flex: 1,
    overflowY: "auto" as const,
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
  },
  commentCard: {
    padding: tokens.spacingVerticalS,
  },
  commentHeader: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
    marginBottom: tokens.spacingVerticalXS,
  },
  commentAuthor: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase200,
  },
  commentTime: {
    color: tokens.colorNeutralForeground3,
    fontSize: tokens.fontSizeBase100,
  },
  commentContent: {
    fontSize: tokens.fontSizeBase200,
    whiteSpace: "pre-wrap" as const,
  },
  componentRef: {
    fontSize: tokens.fontSizeBase100,
    color: tokens.colorBrandForeground1,
    marginTop: tokens.spacingVerticalXS,
  },
  inputArea: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXS,
  },
  sendRow: {
    display: "flex",
    justifyContent: "flex-end",
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

interface CommentPanelProps {
  projectId: string;
  componentRef?: string;
  onClose?: () => void;
}

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString();
}

export default function CommentPanel({
  projectId,
  componentRef,
  onClose,
}: CommentPanelProps) {
  const styles = useStyles();
  const [comments, setComments] = useState<CommentResponseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [newComment, setNewComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadComments = useCallback(async () => {
    setLoading(true);
    try {
      const result = await api.collaboration.listComments(
        projectId,
        componentRef,
      );
      setComments(result.comments);
    } catch {
      // Silently handle — empty state shown
    } finally {
      setLoading(false);
    }
  }, [projectId, componentRef]);

  useEffect(() => {
    loadComments();
  }, [loadComments]);

  const handleSubmit = useCallback(async () => {
    if (!newComment.trim()) return;
    setSubmitting(true);
    try {
      const created = await api.collaboration.addComment(projectId, {
        content: newComment.trim(),
        component_ref: componentRef,
      });
      setComments((prev) => [created, ...prev]);
      setNewComment("");
    } catch {
      // Error handled silently
    } finally {
      setSubmitting(false);
    }
  }, [newComment, projectId, componentRef]);

  return (
    <div className={styles.panel} data-testid="comment-panel">
      <div className={styles.header}>
        <Text className={styles.title}>
          <ChatRegular />
          Comments
          {componentRef && (
            <Text className={styles.componentRef}>
              — {componentRef}
            </Text>
          )}
        </Text>
        {onClose && (
          <Button
            appearance="subtle"
            icon={<DismissRegular />}
            onClick={onClose}
            aria-label="Close comments"
          />
        )}
      </div>

      <Divider />

      <div className={styles.inputArea}>
        <Textarea
          placeholder="Add a comment…"
          value={newComment}
          onChange={(_e, data) => setNewComment(data.value)}
          disabled={submitting}
          resize="vertical"
          data-testid="comment-input"
        />
        <div className={styles.sendRow}>
          <Button
            appearance="primary"
            icon={<SendRegular />}
            onClick={handleSubmit}
            disabled={!newComment.trim() || submitting}
            data-testid="comment-submit"
          >
            Send
          </Button>
        </div>
      </div>

      <Divider />

      {loading ? (
        <div className={styles.loading}>
          <Spinner size="small" label="Loading comments…" />
        </div>
      ) : comments.length === 0 ? (
        <div className={styles.emptyState}>
          <ChatRegular />
          <Text>No comments yet</Text>
        </div>
      ) : (
        <div className={styles.commentList}>
          {comments.map((comment) => (
            <Card
              key={comment.id}
              className={styles.commentCard}
              size="small"
            >
              <div className={styles.commentHeader}>
                <Avatar
                  name={comment.display_name || "User"}
                  size={24}
                />
                <Text className={styles.commentAuthor}>
                  {comment.display_name || "User"}
                </Text>
                <Text className={styles.commentTime}>
                  {formatTimestamp(comment.created_at)}
                </Text>
              </div>
              <Text className={styles.commentContent}>
                {comment.content}
              </Text>
              {comment.component_ref && (
                <Text className={styles.componentRef}>
                  {comment.component_ref}
                </Text>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
