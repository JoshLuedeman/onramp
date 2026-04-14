import { useState, useRef, useCallback, useEffect } from "react";
import {
  Card,
  Text,
  Button,
  Input,
  Badge,
  Spinner,
  makeStyles,
  tokens,
  ProgressBar,
  MessageBar,
  MessageBarBody,
  Divider,
} from "@fluentui/react-components";
import {
  RocketRegular,
  CheckmarkCircleRegular,
  ErrorCircleRegular,
} from "@fluentui/react-icons";
import { useParams } from "react-router-dom";
import { api } from "../services/api";
import type { Architecture } from "../services/api";

const useStyles = makeStyles({
  container: {
    maxWidth: "800px",
    margin: "0 auto",
    padding: "24px",
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  title: {
    fontSize: tokens.fontSizeBase600,
    fontWeight: tokens.fontWeightSemibold,
  },
  card: {
    padding: "20px",
  },
  stepRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "8px 0",
  },
  inputRow: {
    display: "flex",
    gap: "8px",
    alignItems: "end",
  },
});

interface DeploymentStep {
  id: string;
  name: string;
  status: string;
}

export default function DeployPage() {
  const styles = useStyles();
  const { projectId } = useParams<{ projectId: string }>();
  const [subscriptionId, setSubscriptionId] = useState("");
  const [validating, setValidating] = useState(false);
  const [validated, setValidated] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [, setDeploymentId] = useState<string | null>(null);
  const [steps, setSteps] = useState<DeploymentStep[]>([]);
  const [status, setStatus] = useState<string>("idle");
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [architecture, setArchitecture] = useState<Architecture | null>(null);

  useEffect(() => {
    if (projectId) {
      api.architecture.getByProject(projectId).then((data) => {
        if (data.architecture) {
          setArchitecture(data.architecture as Architecture);
        }
      }).catch(console.error);
    } else {
      const stored = sessionStorage.getItem("onramp_architecture");
      if (stored) setArchitecture(JSON.parse(stored));
    }
  }, [projectId]);

  // Poll for deployment status updates
  const pollStatus = useCallback(async (depId: string) => {
    try {
      const resp = await fetch(`/api/deployment/${depId}`);
      if (!resp.ok) return;
      const data = await resp.json();
      setSteps(data.steps || []);
      setStatus(data.status || "unknown");

      // Stop polling when deployment is terminal
      if (["succeeded", "failed", "rolled_back"].includes(data.status)) {
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
        setDeploying(false);
      }
    } catch {
      // Silently retry on next interval
    }
  }, []);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const handleValidate = async () => {
    setValidating(true);
    setError(null);
    try {
      await api.deployment.validate(subscriptionId, "eastus2");
      setValidated(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Validation failed");
    } finally {
      setValidating(false);
    }
  };

  const handleDeploy = async () => {
    if (!architecture) return;
    setDeploying(true);
    setError(null);
    try {
      const resp = await fetch("/api/deployment/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: "default",
          architecture,
          subscription_ids: [subscriptionId],
        }),
      });
      const data = await resp.json();
      const depId = data.id;
      setDeploymentId(depId);
      setSteps(data.steps || []);

      // Start deployment
      const startResp = await fetch(`/api/deployment/${depId}/start`, {
        method: "POST",
      });
      const startData = await startResp.json();
      setSteps(startData.steps || []);
      setStatus(startData.status);

      // Start polling every 3 seconds
      pollRef.current = setInterval(() => pollStatus(depId), 3000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Deployment failed");
      setDeploying(false);
    }
  };

  if (!architecture) {
    return (
      <div className={styles.container}>
        <MessageBar intent="warning">
          <MessageBarBody>
            No architecture found. Please complete the wizard first.
          </MessageBarBody>
        </MessageBar>
      </div>
    );
  }

  const progress =
    steps.length > 0
      ? steps.filter((s) => s.status === "succeeded").length / steps.length
      : 0;

  return (
    <div className={styles.container}>
      <Text className={styles.title}>
        <RocketRegular /> Deploy Landing Zone
      </Text>

      <Card className={styles.card}>
        <Text weight="semibold">Target Subscription</Text>
        <div className={styles.inputRow}>
          <Input
            placeholder="Subscription ID"
            value={subscriptionId}
            onChange={(_, d) => setSubscriptionId(d.value)}
            style={{ flex: 1 }}
          />
          <Button
            appearance="primary"
            onClick={handleValidate}
            disabled={!subscriptionId || validating}
          >
            {validating ? <Spinner size="tiny" /> : "Validate"}
          </Button>
        </div>
        {validated && (
          <MessageBar intent="success" style={{ marginTop: 8 }}>
            <MessageBarBody>Subscription validated successfully.</MessageBarBody>
          </MessageBar>
        )}
      </Card>

      {validated && (
        <Card className={styles.card}>
          <Text weight="semibold">Deployment</Text>
          {status === "idle" && (
            <Button
              appearance="primary"
              icon={<RocketRegular />}
              onClick={handleDeploy}
              disabled={deploying}
              style={{ marginTop: 8 }}
            >
              {deploying ? "Deploying..." : "Deploy to Azure"}
            </Button>
          )}
          {steps.length > 0 && (
            <>
              <ProgressBar value={progress} style={{ margin: "12px 0" }} />
              <Text>{Math.round(progress * 100)}% complete</Text>
              <Divider style={{ margin: "8px 0" }} />
              {steps.map((step) => (
                <div key={step.id} className={styles.stepRow}>
                  <Text>{step.name}</Text>
                  <Badge
                    color={
                      step.status === "succeeded"
                        ? "success"
                        : step.status === "failed"
                        ? "danger"
                        : "informative"
                    }
                  >
                    {step.status === "succeeded" && <CheckmarkCircleRegular />}
                    {step.status === "failed" && <ErrorCircleRegular />}
                    {step.status}
                  </Badge>
                </div>
              ))}
            </>
          )}
        </Card>
      )}

      {error && (
        <MessageBar intent="error">
          <MessageBarBody>{error}</MessageBarBody>
        </MessageBar>
      )}
    </div>
  );
}
