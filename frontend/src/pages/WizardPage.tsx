import { useState, useEffect, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  makeStyles,
  Spinner,
  Title1,
  Button,
  Text,
  tokens,
  Dialog,
  DialogSurface,
  DialogTitle,
  DialogBody,
  DialogActions,
  Body1,
} from "@fluentui/react-components";
import { ArrowLeftRegular, ArrowResetRegular } from "@fluentui/react-icons";
import QuestionCard from "../components/wizard/QuestionCard";
import WizardProgressBar from "../components/wizard/ProgressBar";
import WizardComplete from "../components/wizard/WizardComplete";
import UnsureReview from "../components/wizard/UnsureReview";
import type { Question, Progress } from "../services/api";
import { api } from "../services/api";

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    padding: "48px 24px",
    minHeight: "calc(100vh - 52px)",
  },
  title: {
    marginBottom: "32px",
    color: tokens.colorBrandForeground1,
  },
  spinner: {
    marginTop: "48px",
  },
  backButton: {
    alignSelf: "flex-start",
    maxWidth: "640px",
    width: "100%",
    marginBottom: "8px",
  },
  navRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    maxWidth: "640px",
    width: "100%",
    marginBottom: "8px",
  },
  autoSaveIndicator: {
    color: tokens.colorNeutralForeground3,
    fontSize: tokens.fontSizeBase200,
    marginTop: "4px",
    textAlign: "center" as const,
  },
});

export default function WizardPage() {
  const styles = useStyles();
  const navigate = useNavigate();
  const { projectId } = useParams<{ projectId: string }>();
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [questionHistory, setQuestionHistory] = useState<Question[]>([]);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [recommendations, setRecommendations] = useState<
    { question_id: string; recommended_value: string; reason: string }[]
  >([]);
  const [resolvedAnswers, setResolvedAnswers] = useState<Record<string, string | string[]> | null>(null);
  const [restoringState, setRestoringState] = useState(false);
  const [conflictData, setConflictData] = useState<{
    local: Record<string, string | string[]>;
    server: Record<string, string | string[]>;
  } | null>(null);

  const fetchNext = useCallback(async (currentAnswers: Record<string, string | string[]>) => {
    setLoading(true);
    try {
      const data = await api.questionnaire.getNextQuestion(currentAnswers);
      if (data.complete) {
        setIsComplete(true);
        setCurrentQuestion(null);
        // Resolve unsure answers
        try {
          const unsureResult = await api.questionnaire.resolveUnsure(currentAnswers);
          if (unsureResult.recommendations.length > 0) {
            setRecommendations(unsureResult.recommendations);
            setResolvedAnswers(unsureResult.resolved_answers);
          } else {
            setRecommendations([]);
            setResolvedAnswers(null);
          }
        } catch (err) {
          console.error("Failed to resolve unsure answers:", err);
          setRecommendations([]);
          setResolvedAnswers(null);
        }
      } else {
        setCurrentQuestion(data.question);
        setProgress(data.progress || null);
        setIsComplete(false);
      }
    } catch (error) {
      console.error("Failed to fetch next question:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (projectId) {
      setRestoringState(true);
      let localAnswers: Record<string, string | string[]> | null = null;
      try {
        const localSaved = sessionStorage.getItem("onramp_wizard_answers");
        localAnswers = localSaved ? JSON.parse(localSaved) as Record<string, string | string[]> : null;
      } catch {
        localAnswers = null;
      }

      api.questionnaire.loadState(projectId).then((data) => {
        const serverAnswers = data.answers && Object.keys(data.answers).length > 0
          ? data.answers : null;

        // Conflict: both local and server state exist with different content
        if (localAnswers && Object.keys(localAnswers).length > 0 && serverAnswers
            && JSON.stringify(localAnswers) !== JSON.stringify(serverAnswers)) {
          setConflictData({ local: localAnswers, server: serverAnswers });
          setRestoringState(false);
        } else if (serverAnswers) {
          setAnswers(serverAnswers);
          fetchNext(serverAnswers);
          setRestoringState(false);
        } else if (localAnswers && Object.keys(localAnswers).length > 0) {
          setAnswers(localAnswers);
          fetchNext(localAnswers);
          setRestoringState(false);
        } else {
          fetchNext({});
          setRestoringState(false);
        }
      }).catch(() => {
        if (localAnswers && Object.keys(localAnswers).length > 0) {
          setAnswers(localAnswers);
          fetchNext(localAnswers);
        } else {
          fetchNext({});
        }
        setRestoringState(false);
      });
    } else {
      const saved = sessionStorage.getItem("onramp_wizard_answers");
      if (saved) {
        try {
          const savedAnswers = JSON.parse(saved);
          setAnswers(savedAnswers);
          fetchNext(savedAnswers);
        } catch {
          fetchNext({});
        }
      } else {
        fetchNext({});
      }
    }
  }, [projectId, fetchNext]);

  const handleConflictResolve = (choice: "local" | "server") => {
    if (!conflictData) return;
    const chosen = choice === "local" ? conflictData.local : conflictData.server;
    setAnswers(chosen);
    setConflictData(null);
    if (projectId) {
      api.questionnaire.saveState(projectId, chosen).catch(console.error);
    }
    sessionStorage.setItem("onramp_wizard_answers", JSON.stringify(chosen));
    fetchNext(chosen);
  };

  const handleAnswer = (questionId: string, answer: string | string[]) => {
    if (currentQuestion) {
      setQuestionHistory((prev) => [...prev, currentQuestion]);
    }
    const newAnswers = { ...answers, [questionId]: answer };
    setAnswers(newAnswers);
    if (!projectId) {
      sessionStorage.setItem("onramp_wizard_answers", JSON.stringify(newAnswers));
    }
    if (projectId) {
      api.questionnaire.saveState(projectId, newAnswers).catch(console.error);
    }
    fetchNext(newAnswers);
  };

  const handleBack = () => {
    if (questionHistory.length === 0) return;
    const prevQuestion = questionHistory[questionHistory.length - 1];
    setQuestionHistory((prev) => prev.slice(0, -1));

    // Remove the answer for the previous question so it shows as unanswered
    const newAnswers = { ...answers };
    delete newAnswers[prevQuestion.id];
    setAnswers(newAnswers);

    setCurrentQuestion(prevQuestion);
    setIsComplete(false);

    // Update progress
    if (progress) {
      setProgress({
        ...progress,
        answered: progress.answered - 1,
        remaining: progress.remaining + 1,
        percent_complete: Math.round(((progress.answered - 1) / progress.total) * 100),
      });
    }
  };

  const handleStartOver = () => {
    sessionStorage.removeItem("onramp_wizard_answers");
    setAnswers({});
    setQuestionHistory([]);
    setCurrentQuestion(null);
    setIsComplete(false);
    setRecommendations([]);
    setResolvedAnswers(null);
    fetchNext({});
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const finalAnswers = resolvedAnswers || answers;
      const result = await api.architecture.generate(
        finalAnswers,
        false,
        projectId ? { project_id: projectId, use_archetype: true } : undefined
      );
      if (!projectId) {
        sessionStorage.setItem("onramp_architecture", JSON.stringify(result.architecture));
        sessionStorage.setItem("onramp_answers", JSON.stringify(finalAnswers));
      }
      navigate(projectId ? `/projects/${projectId}/architecture` : "/architecture");
    } catch (error) {
      console.error("Failed to generate architecture:", error);
    } finally {
      setGenerating(false);
    }
  };

  const handleAcceptRecommendations = (accepted: Record<string, string | string[]>) => {
    const finalAnswers = { ...answers, ...accepted };
    setResolvedAnswers(finalAnswers);
    setRecommendations([]);
  };

  return (
    <div className={styles.container}>
      <Title1 className={styles.title}>Design Your Landing Zone</Title1>

      {/* Conflict resolution dialog */}
      <Dialog open={conflictData !== null}>
        <DialogSurface>
          <DialogTitle>State Conflict Detected</DialogTitle>
          <DialogBody>
            <Body1>
              Both local and server-saved progress exist for this project.
              Local has {conflictData ? Object.keys(conflictData.local).length : 0} answers,
              server has {conflictData ? Object.keys(conflictData.server).length : 0} answers.
              Which would you like to continue with?
            </Body1>
          </DialogBody>
          <DialogActions>
            <Button appearance="secondary" onClick={() => handleConflictResolve("local")}>
              Use Local
            </Button>
            <Button appearance="primary" onClick={() => handleConflictResolve("server")}>
              Use Server
            </Button>
          </DialogActions>
        </DialogSurface>
      </Dialog>

      {(loading || restoringState) && <Spinner className={styles.spinner} label={restoringState ? "Restoring progress..." : "Loading..."} size="large" />}

      {!loading && !isComplete && progress && <WizardProgressBar progress={progress} />}

      {!loading && !isComplete && Object.keys(answers).length > 0 && (
        <Text className={styles.autoSaveIndicator}>Progress auto-saved ✓</Text>
      )}

      {!loading && !isComplete && questionHistory.length > 0 && (
        <div className={styles.navRow}>
          <Button
            appearance="subtle"
            icon={<ArrowLeftRegular />}
            onClick={handleBack}
            size="medium"
          >
            Back
          </Button>
          <Button
            appearance="outline"
            icon={<ArrowResetRegular />}
            onClick={handleStartOver}
            size="small"
          >
            Start Over
          </Button>
        </div>
      )}

      {!loading && !isComplete && currentQuestion && (
        <QuestionCard
          question={currentQuestion}
          onAnswer={handleAnswer}
          existingAnswer={answers[currentQuestion.id]}
        />
      )}

      {!loading && isComplete && !generating && (
        <>
          <div className={styles.navRow}>
            <Button
              appearance="subtle"
              icon={<ArrowLeftRegular />}
              onClick={handleBack}
              size="medium"
            >
              Back
            </Button>
            <Button
              appearance="outline"
              icon={<ArrowResetRegular />}
              onClick={handleStartOver}
              size="small"
            >
              Start Over
            </Button>
          </div>
          {recommendations.length > 0 ? (
            <UnsureReview
              recommendations={recommendations}
              onAccept={handleAcceptRecommendations}
            />
          ) : (
            <WizardComplete onGenerate={handleGenerate} answeredCount={Object.keys(answers).length} />
          )}
        </>
      )}

      {generating && <Spinner className={styles.spinner} label="Generating your architecture..." size="large" />}
    </div>
  );
}
