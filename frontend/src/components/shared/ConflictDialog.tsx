import {
  Badge,
  Body1,
  Button,
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogSurface,
  DialogTitle,
  Divider,
  makeStyles,
  MessageBar,
  MessageBarBody,
  Text,
  tokens,
} from "@fluentui/react-components";
import {
  ArrowSyncRegular,
  DismissRegular,
  SaveRegular,
  WarningRegular,
} from "@fluentui/react-icons";
import type { ConflictResponse } from "../../services/api";

export interface ConflictDialogProps {
  open: boolean;
  conflict: ConflictResponse | null;
  onOverwrite: () => void;
  onMerge: () => void;
  onCancel: () => void;
}

const useStyles = makeStyles({
  surface: {
    maxWidth: "560px",
  },
  warningIcon: {
    color: tokens.colorPaletteYellowForeground1,
    fontSize: "24px",
    marginRight: tokens.spacingHorizontalS,
  },
  titleRow: {
    display: "flex",
    alignItems: "center",
  },
  versionInfo: {
    display: "flex",
    gap: tokens.spacingHorizontalL,
    marginTop: tokens.spacingVerticalM,
    marginBottom: tokens.spacingVerticalM,
    paddingTop: tokens.spacingVerticalM,
    paddingRight: tokens.spacingHorizontalM,
    paddingBottom: tokens.spacingVerticalM,
    paddingLeft: tokens.spacingHorizontalM,
    backgroundColor: tokens.colorNeutralBackground3,
    borderRadius: tokens.borderRadiusMedium,
  },
  versionCol: {
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXS,
  },
  message: {
    marginTop: tokens.spacingVerticalS,
  },
  actions: {
    display: "flex",
    gap: tokens.spacingHorizontalS,
    justifyContent: "flex-end",
  },
  divider: {
    marginTop: tokens.spacingVerticalM,
    marginBottom: tokens.spacingVerticalM,
  },
});

export default function ConflictDialog({
  open,
  conflict,
  onOverwrite,
  onMerge,
  onCancel,
}: ConflictDialogProps) {
  const styles = useStyles();

  if (!conflict) return null;

  return (
    <Dialog open={open} onOpenChange={(_e, data) => {
      if (!data.open) onCancel();
    }}>
      <DialogSurface className={styles.surface} aria-label="Conflict dialog">
        <DialogBody>
          <DialogTitle>
            <div className={styles.titleRow}>
              <WarningRegular className={styles.warningIcon} />
              <Text weight="semibold" size={500}>
                Version Conflict
              </Text>
            </div>
          </DialogTitle>
          <DialogContent>
            <MessageBar intent="warning">
              <MessageBarBody>
                This resource has been modified by another user or session
                since you started editing.
              </MessageBarBody>
            </MessageBar>

            <div className={styles.versionInfo}>
              <div className={styles.versionCol}>
                <Text size={200} weight="semibold">
                  Your version
                </Text>
                <Badge appearance="outline" color="danger">
                  v{conflict.submitted_version}
                </Badge>
              </div>
              <div className={styles.versionCol}>
                <Text size={200} weight="semibold">
                  Current version
                </Text>
                <Badge appearance="outline" color="success">
                  v{conflict.current_version}
                </Badge>
              </div>
            </div>

            <Body1 className={styles.message}>
              {conflict.message}
            </Body1>

            <Divider className={styles.divider} />

            <Body1>
              Choose how to resolve this conflict:
            </Body1>
            <ul>
              <li>
                <Text weight="semibold">Overwrite</Text> — Replace the
                current version with your changes (discards others'
                edits)
              </li>
              <li>
                <Text weight="semibold">Merge</Text> — Reload the
                latest version and re-apply your changes
              </li>
              <li>
                <Text weight="semibold">Cancel</Text> — Discard your
                changes and keep the current version
              </li>
            </ul>
          </DialogContent>
          <DialogActions className={styles.actions}>
            <Button
              appearance="secondary"
              icon={<DismissRegular />}
              onClick={onCancel}
              data-testid="conflict-cancel"
            >
              Cancel
            </Button>
            <Button
              appearance="secondary"
              icon={<ArrowSyncRegular />}
              onClick={onMerge}
              data-testid="conflict-merge"
            >
              Merge
            </Button>
            <Button
              appearance="primary"
              icon={<SaveRegular />}
              onClick={onOverwrite}
              data-testid="conflict-overwrite"
            >
              Overwrite
            </Button>
          </DialogActions>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  );
}
