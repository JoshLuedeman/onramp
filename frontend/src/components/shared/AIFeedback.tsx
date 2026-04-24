/**
 * AIFeedback — reusable thumbs-up / thumbs-down feedback widget.
 *
 * Renders two icon buttons (positive / negative).  On negative feedback a
 * dialog opens for an optional text comment.  Calls `onFeedback` when the
 * user confirms.
 */

import { useState } from "react";
import {
  makeStyles,
  tokens,
  Button,
  Dialog,
  DialogSurface,
  DialogTitle,
  DialogBody,
  DialogActions,
  DialogContent,
  Textarea,
  Text,
  Tooltip,
} from "@fluentui/react-components";
import {
  ThumbLike24Regular,
  ThumbDislike24Regular,
} from "@fluentui/react-icons";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export type FeedbackRating = "positive" | "negative";

export interface FeedbackPayload {
  feature: string;
  outputId: string;
  rating: FeedbackRating;
  comment?: string;
}

export interface AIFeedbackProps {
  /** Which AI feature produced the output (e.g. "architecture"). */
  feature: string;
  /** Unique identifier for the AI output being rated. */
  outputId: string;
  /** Called when the user submits feedback. */
  onFeedback?: (payload: FeedbackPayload) => void;
}

/* ------------------------------------------------------------------ */
/*  Styles                                                             */
/* ------------------------------------------------------------------ */

const useStyles = makeStyles({
  root: {
    display: "inline-flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
  },
  selected: {
    color: tokens.colorBrandForeground1,
  },
  label: {
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
  },
  fullWidth: {
    width: "100%",
  },
});

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function AIFeedback({
  feature,
  outputId,
  onFeedback,
}: AIFeedbackProps) {
  const styles = useStyles();
  const [selected, setSelected] = useState<FeedbackRating | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [comment, setComment] = useState("");

  const handlePositive = () => {
    setSelected("positive");
    onFeedback?.({ feature, outputId, rating: "positive" });
  };

  const handleNegativeClick = () => {
    setSelected("negative");
    setDialogOpen(true);
  };

  const handleDialogSubmit = () => {
    onFeedback?.({
      feature,
      outputId,
      rating: "negative",
      comment: comment.trim() || undefined,
    });
    setDialogOpen(false);
    setComment("");
  };

  const handleDialogCancel = () => {
    // Still send the negative rating, just without a comment
    onFeedback?.({ feature, outputId, rating: "negative" });
    setDialogOpen(false);
    setComment("");
  };

  return (
    <div className={styles.root} data-testid="ai-feedback">
      <Text className={styles.label}>Was this helpful?</Text>
      <Tooltip content="Helpful" relationship="label">
        <Button
          appearance="subtle"
          icon={<ThumbLike24Regular />}
          className={selected === "positive" ? styles.selected : undefined}
          onClick={handlePositive}
          aria-label="Thumbs up"
          size="small"
        />
      </Tooltip>
      <Tooltip content="Not helpful" relationship="label">
        <Button
          appearance="subtle"
          icon={<ThumbDislike24Regular />}
          className={selected === "negative" ? styles.selected : undefined}
          onClick={handleNegativeClick}
          aria-label="Thumbs down"
          size="small"
        />
      </Tooltip>

      {/* Comment dialog on negative feedback */}
      <Dialog open={dialogOpen} onOpenChange={(_, data) => setDialogOpen(data.open)}>
        <DialogSurface aria-label="Feedback comment dialog">
          <DialogTitle>What could be improved?</DialogTitle>
          <DialogBody>
            <DialogContent>
              <Textarea
                className={styles.fullWidth}
                placeholder="Optional: tell us what went wrong…"
                value={comment}
                onChange={(_, data) => setComment(data.value)}
                resize="vertical"
                aria-label="Feedback comment"
              />
            </DialogContent>
          </DialogBody>
          <DialogActions>
            <Button appearance="secondary" onClick={handleDialogCancel}>
              Skip
            </Button>
            <Button appearance="primary" onClick={handleDialogSubmit}>
              Submit
            </Button>
          </DialogActions>
        </DialogSurface>
      </Dialog>
    </div>
  );
}
