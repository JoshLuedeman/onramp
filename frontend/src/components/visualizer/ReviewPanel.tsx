import { useCallback, useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogSurface,
  DialogTitle,
  DialogTrigger,
  Divider,
  ProgressBar,
  Spinner,
  Text,
  Textarea,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  CheckmarkCircleRegular,
  DismissCircleRegular,
  EditRegular,
  LockClosedRegular,
  SendRegular,
  ShieldCheckmarkRegular,
} from "@fluentui/react-icons";
import { api } from "../../services/api";
import type {
  ReviewResponseItem,
  ReviewStatusResponse,
} from "../../services/api";

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
  statusSection: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
    padding: tokens.spacingVerticalS,
  },
  statusRow: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
  },
  progressSection: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXS,
  },
  progressLabel: {
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
  },
  actionButtons: {
    display: "flex",
    gap: tokens.spacingHorizontalS,
    flexWrap: "wrap" as const,
  },
  reviewForm: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXS,
  },
  reviewList: {
    flex: 1,
    overflowY: "auto" as const,
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
  },
  reviewCard: {
    padding: tokens.spacingVerticalS,
  },
  reviewHeader: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
    marginBottom: tokens.spacingVerticalXS,
  },
  reviewTime: {
    color: tokens.colorNeutralForeground3,
    fontSize: tokens.fontSizeBase100,
  },
  reviewComments: {
    fontSize: tokens.fontSizeBase200,
    whiteSpace: "pre-wrap" as const,
    marginTop: tokens.spacingVerticalXS,
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
  lockIndicator: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalXS,
    color: tokens.colorPaletteRedForeground1,
    fontSize: tokens.fontSizeBase200,
  },
});

interface ReviewPanelProps {
  architectureId: string;
  onClose?: () => void;
}

const STATUS_BADGE_MAP: Record<
  string,
  {
    color: "informative" | "success" | "warning" | "danger" | "important";
    label: string;
  }
> = {
  draft: { color: "informative", label: "Draft" },
  in_review: { color: "warning", label: "In Review" },
  approved: { color: "success", label: "Approved" },
  rejected: { color: "danger", label: "Rejected" },
  deployed: { color: "important", label: "Deployed" },
};

const ACTION_BADGE_MAP: Record<
  string,
  { color: "success" | "warning" | "danger"; label: string }
> = {
  approved: { color: "success", label: "Approved" },
  changes_requested: { color: "warning", label: "Changes Requested" },
  rejected: { color: "danger", label: "Rejected" },
};

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString();
}

export default function ReviewPanel({
  architectureId,
  onClose,
}: ReviewPanelProps) {
  const styles = useStyles();
  const [status, setStatus] = useState<ReviewStatusResponse | null>(null);
  const [reviews, setReviews] = useState<ReviewResponseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [reviewComment, setReviewComment] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [statusData, historyData] = await Promise.all([
        api.reviews.getStatus(architectureId),
        api.reviews.getHistory(architectureId),
      ]);
      setStatus(statusData);
      setReviews(historyData.reviews);
    } catch {
      // Error handled — empty state shown
    } finally {
      setLoading(false);
    }
  }, [architectureId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSubmitForReview = useCallback(async () => {
    setSubmitting(true);
    try {
      await api.reviews.submit(architectureId);
      await loadData();
    } catch {
      // Error silently handled
    } finally {
      setSubmitting(false);
    }
  }, [architectureId, loadData]);

  const handleWithdraw = useCallback(async () => {
    setSubmitting(true);
    try {
      await api.reviews.withdraw(architectureId);
      await loadData();
    } catch {
      // Error silently handled
    } finally {
      setSubmitting(false);
    }
  }, [architectureId, loadData]);

  const handleReviewAction = useCallback(
    async (action: "approved" | "changes_requested" | "rejected") => {
      setPendingAction(action);
      setDialogOpen(true);
    },
    [],
  );

  const confirmReviewAction = useCallback(async () => {
    if (!pendingAction) return;
    setSubmitting(true);
    setDialogOpen(false);
    try {
      await api.reviews.perform(architectureId, {
        action: pendingAction as "approved" | "changes_requested" | "rejected",
        comments: reviewComment || undefined,
      });
      setReviewComment("");
      setPendingAction(null);
      await loadData();
    } catch {
      // Error silently handled
    } finally {
      setSubmitting(false);
    }
  }, [architectureId, pendingAction, reviewComment, loadData]);

  if (loading) {
    return (
      <div className={styles.panel} data-testid="review-panel">
        <div className={styles.loading}>
          <Spinner size="small" label="Loading review status…" />
        </div>
      </div>
    );
  }

  const badgeInfo = STATUS_BADGE_MAP[status?.status ?? "draft"] ??
    STATUS_BADGE_MAP.draft;
  const approvalProgress =
    status && status.approvals_needed > 0
      ? status.approvals_received / status.approvals_needed
      : 0;

  return (
    <div className={styles.panel} data-testid="review-panel">
      <div className={styles.header}>
        <Text className={styles.title}>
          <ShieldCheckmarkRegular />
          Architecture Review
        </Text>
        {onClose && (
          <Button
            appearance="subtle"
            icon={<DismissCircleRegular />}
            onClick={onClose}
            aria-label="Close review panel"
          />
        )}
      </div>

      <Divider />

      {/* Status Section */}
      <div className={styles.statusSection}>
        <div className={styles.statusRow}>
          <Text>Status:</Text>
          <Badge
            appearance="filled"
            color={badgeInfo.color}
            data-testid="review-status-badge"
          >
            {badgeInfo.label}
          </Badge>
          {status?.is_locked && (
            <span
              className={styles.lockIndicator}
              data-testid="lock-indicator"
            >
              <LockClosedRegular />
              Locked
            </span>
          )}
        </div>

        {/* Approval Progress */}
        <div className={styles.progressSection}>
          <Text className={styles.progressLabel}>
            {status?.approvals_received ?? 0} of{" "}
            {status?.approvals_needed ?? 1} approvals
          </Text>
          <ProgressBar
            value={approvalProgress}
            max={1}
            data-testid="approval-progress"
          />
        </div>
      </div>

      <Divider />

      {/* Action Buttons */}
      <div className={styles.actionButtons}>
        {status?.status === "draft" && (
          <Button
            appearance="primary"
            icon={<SendRegular />}
            onClick={handleSubmitForReview}
            disabled={submitting}
            data-testid="submit-for-review-btn"
          >
            Submit for Review
          </Button>
        )}

        {(status?.status === "in_review" ||
          status?.status === "rejected") && (
          <Button
            appearance="subtle"
            icon={<EditRegular />}
            onClick={handleWithdraw}
            disabled={submitting}
            data-testid="withdraw-btn"
          >
            Withdraw
          </Button>
        )}

        {status?.status === "in_review" && (
          <>
            <Button
              appearance="primary"
              icon={<CheckmarkCircleRegular />}
              onClick={() => handleReviewAction("approved")}
              disabled={submitting}
              data-testid="approve-btn"
            >
              Approve
            </Button>
            <Button
              appearance="outline"
              onClick={() => handleReviewAction("changes_requested")}
              disabled={submitting}
              data-testid="request-changes-btn"
            >
              Request Changes
            </Button>
            <Button
              appearance="outline"
              icon={<DismissCircleRegular />}
              onClick={() => handleReviewAction("rejected")}
              disabled={submitting}
              data-testid="reject-btn"
            >
              Reject
            </Button>
          </>
        )}
      </div>

      <Divider />

      {/* Review History */}
      <Text className={styles.title}>Review History</Text>

      {reviews.length === 0 ? (
        <div className={styles.emptyState} data-testid="empty-reviews">
          <ShieldCheckmarkRegular />
          <Text>No reviews yet</Text>
        </div>
      ) : (
        <div className={styles.reviewList} data-testid="review-list">
          {reviews.map((review) => {
            const actionInfo = ACTION_BADGE_MAP[review.action] ?? {
              color: "warning" as const,
              label: review.action,
            };
            return (
              <Card
                key={review.id}
                className={styles.reviewCard}
                size="small"
              >
                <div className={styles.reviewHeader}>
                  <Badge
                    appearance="filled"
                    color={actionInfo.color}
                  >
                    {actionInfo.label}
                  </Badge>
                  <Text className={styles.reviewTime}>
                    {formatTimestamp(review.created_at)}
                  </Text>
                </div>
                {review.comments && (
                  <Text className={styles.reviewComments}>
                    {review.comments}
                  </Text>
                )}
              </Card>
            );
          })}
        </div>
      )}

      {/* Review Action Dialog */}
      <Dialog open={dialogOpen} onOpenChange={(_e, data) => setDialogOpen(data.open)}>
        <DialogSurface>
          <DialogBody>
            <DialogTitle>
              {pendingAction === "approved"
                ? "Approve Architecture"
                : pendingAction === "rejected"
                  ? "Reject Architecture"
                  : "Request Changes"}
            </DialogTitle>
            <DialogContent>
              <div className={styles.reviewForm}>
                <Textarea
                  placeholder="Add comments (optional)…"
                  value={reviewComment}
                  onChange={(_e, data) => setReviewComment(data.value)}
                  resize="vertical"
                  data-testid="review-comment-input"
                />
              </div>
            </DialogContent>
            <DialogActions>
              <DialogTrigger disableButtonEnhancement>
                <Button
                  appearance="secondary"
                  data-testid="cancel-review-btn"
                >
                  Cancel
                </Button>
              </DialogTrigger>
              <Button
                appearance="primary"
                onClick={confirmReviewAction}
                disabled={submitting}
                data-testid="confirm-review-btn"
              >
                Confirm
              </Button>
            </DialogActions>
          </DialogBody>
        </DialogSurface>
      </Dialog>
    </div>
  );
}
