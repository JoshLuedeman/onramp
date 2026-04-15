import {
  makeStyles,
  tokens,
  Text,
  Button,
  Card,
  CardHeader,
  CardFooter,
  ProgressBar,
} from "@fluentui/react-components";
import {
  DismissRegular,
  ChevronLeftRegular,
  ChevronRightRegular,
} from "@fluentui/react-icons";
import type { TutorialStep } from "../../hooks/useTutorial";

export interface TutorialOverlayProps {
  isActive: boolean;
  currentStep: TutorialStep | null;
  currentStepIndex: number;
  totalSteps: number;
  onNext: () => void;
  onPrev: () => void;
  onSkip: () => void;
}

const useStyles = makeStyles({
  backdrop: {
    position: "fixed",
    top: "0",
    left: "0",
    width: "100vw",
    height: "100vh",
    backgroundColor: "rgba(0, 0, 0, 0.4)",
    zIndex: 1000,
    display: "flex",
    justifyContent: "center",
    alignItems: "flex-start",
    paddingTop: "80px",
  },
  card: {
    maxWidth: "440px",
    width: "100%",
    zIndex: 1001,
    boxShadow: tokens.shadow16,
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  },
  title: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase400,
  },
  content: {
    padding: `0 ${tokens.spacingHorizontalL} ${tokens.spacingVerticalM}`,
    color: tokens.colorNeutralForeground2,
    fontSize: tokens.fontSizeBase300,
    lineHeight: tokens.lineHeightBase300,
  },
  progress: {
    padding: `0 ${tokens.spacingHorizontalL} ${tokens.spacingVerticalS}`,
  },
  progressLabel: {
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
    display: "block",
    marginBottom: tokens.spacingVerticalXS,
  },
  footer: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
  },
  navButtons: {
    display: "flex",
    gap: tokens.spacingHorizontalS,
  },
});

export default function TutorialOverlay({
  isActive,
  currentStep,
  currentStepIndex,
  totalSteps,
  onNext,
  onPrev,
  onSkip,
}: TutorialOverlayProps) {
  const styles = useStyles();

  if (!isActive || !currentStep) {
    return null;
  }

  const isFirstStep = currentStepIndex === 0;
  const isLastStep = currentStepIndex === totalSteps - 1;
  const progressValue = (currentStepIndex + 1) / totalSteps;

  return (
    <div className={styles.backdrop} data-testid="tutorial-overlay">
      <Card className={styles.card} role="dialog" aria-label="Tutorial">
        <CardHeader
          header={
            <div className={styles.header}>
              <Text className={styles.title}>{currentStep.title}</Text>
              <Button
                appearance="subtle"
                icon={<DismissRegular />}
                onClick={onSkip}
                aria-label="Skip tutorial"
                size="small"
              />
            </div>
          }
        />
        <div className={styles.content}>{currentStep.content}</div>
        <div className={styles.progress}>
          <Text className={styles.progressLabel}>
            Step {currentStepIndex + 1} of {totalSteps}
          </Text>
          <ProgressBar value={progressValue} thickness="large" />
        </div>
        <CardFooter>
          <div className={styles.footer}>
            <Button appearance="subtle" onClick={onSkip} size="small">
              Skip
            </Button>
            <div className={styles.navButtons}>
              <Button
                appearance="outline"
                icon={<ChevronLeftRegular />}
                onClick={onPrev}
                disabled={isFirstStep}
                size="small"
                aria-label="Previous step"
              >
                Back
              </Button>
              <Button
                appearance="primary"
                icon={<ChevronRightRegular />}
                iconPosition="after"
                onClick={onNext}
                size="small"
                aria-label={isLastStep ? "Finish tutorial" : "Next step"}
              >
                {isLastStep ? "Finish" : "Next"}
              </Button>
            </div>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
