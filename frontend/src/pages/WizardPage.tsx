import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { makeStyles, Spinner, Title1, tokens } from "@fluentui/react-components";
import QuestionCard from "../components/wizard/QuestionCard";
import WizardProgressBar from "../components/wizard/ProgressBar";
import WizardComplete from "../components/wizard/WizardComplete";
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
});

export default function WizardPage() {
  const styles = useStyles();
  const navigate = useNavigate();
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const fetchNext = useCallback(async (currentAnswers: Record<string, string | string[]>) => {
    setLoading(true);
    try {
      const data = await api.questionnaire.getNextQuestion(currentAnswers);
      if (data.complete) {
        setIsComplete(true);
        setCurrentQuestion(null);
      } else {
        setCurrentQuestion(data.question);
        setProgress(data.progress || null);
      }
    } catch (error) {
      console.error("Failed to fetch next question:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNext(answers);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleAnswer = (questionId: string, answer: string | string[]) => {
    const newAnswers = { ...answers, [questionId]: answer };
    setAnswers(newAnswers);
    fetchNext(newAnswers);
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const result = await api.architecture.generate(answers);
      // Store in session for the architecture page
      sessionStorage.setItem("onramp_architecture", JSON.stringify(result.architecture));
      sessionStorage.setItem("onramp_answers", JSON.stringify(answers));
      navigate("/architecture");
    } catch (error) {
      console.error("Failed to generate architecture:", error);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className={styles.container}>
      <Title1 className={styles.title}>Design Your Landing Zone</Title1>

      {loading && <Spinner className={styles.spinner} label="Loading..." size="large" />}

      {!loading && !isComplete && progress && <WizardProgressBar progress={progress} />}

      {!loading && !isComplete && currentQuestion && (
        <QuestionCard
          question={currentQuestion}
          onAnswer={handleAnswer}
          existingAnswer={answers[currentQuestion.id]}
        />
      )}

      {!loading && isComplete && !generating && (
        <WizardComplete onGenerate={handleGenerate} answeredCount={Object.keys(answers).length} />
      )}

      {generating && <Spinner className={styles.spinner} label="Generating your architecture..." size="large" />}
    </div>
  );
}
