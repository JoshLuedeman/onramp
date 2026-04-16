import { useState, useCallback } from "react";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  Tab,
  TabList,
  Text,
  Textarea,
  makeStyles,
  tokens,
} from "@fluentui/react-components";

import { api } from "../../services/api";
import type {
  PolicyDefinition as PolicyDefinitionType,
  PolicyTemplate as PolicyTemplateType,
  PolicyValidationResult as PolicyValidationResultType,
} from "../../services/api";

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: "16px",
    padding: "16px",
  },
  inputSection: {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  },
  buttonRow: {
    display: "flex",
    gap: "8px",
    alignItems: "center",
  },
  previewCard: {
    marginTop: "8px",
  },
  codeBlock: {
    backgroundColor: tokens.colorNeutralBackground3,
    padding: "12px",
    borderRadius: "4px",
    fontFamily: "monospace",
    fontSize: tokens.fontSizeBase200,
    overflow: "auto",
    maxHeight: "400px",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  },
  validationRow: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    marginTop: "4px",
  },
  templateCard: {
    cursor: "pointer",
    marginBottom: "8px",
  },
  templateList: {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
    marginTop: "8px",
  },
  errorText: {
    color: tokens.colorPaletteRedForeground1,
    fontSize: tokens.fontSizeBase200,
  },
  label: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase200,
  },
});

export default function PolicyCreator() {
  const styles = useStyles();
  const [activeTab, setActiveTab] = useState<string>("generate");
  const [description, setDescription] = useState("");
  const [generatedPolicy, setGeneratedPolicy] = useState<PolicyDefinitionType | null>(null);
  const [validation, setValidation] = useState<PolicyValidationResultType | null>(null);
  const [templates, setTemplates] = useState<PolicyTemplateType[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [libraryLoaded, setLibraryLoaded] = useState(false);

  const handleGenerate = useCallback(async () => {
    if (!description.trim()) return;
    setLoading(true);
    setError(null);
    setValidation(null);
    try {
      const result = await api.policies.generate(description);
      setGeneratedPolicy(result);
      // Auto-validate the generated policy
      const validationResult = await api.policies.validate(result);
      setValidation(validationResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  }, [description]);

  const handleApply = useCallback(async () => {
    if (!generatedPolicy) return;
    setLoading(true);
    setError(null);
    try {
      await api.policies.apply(generatedPolicy);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to apply policy");
    } finally {
      setLoading(false);
    }
  }, [generatedPolicy]);

  const handleLoadLibrary = useCallback(async () => {
    if (libraryLoaded) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.policies.getLibrary();
      setTemplates(result);
      setLibraryLoaded(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load library");
    } finally {
      setLoading(false);
    }
  }, [libraryLoaded]);

  const handleSelectTemplate = useCallback(
    (template: PolicyTemplateType) => {
      setGeneratedPolicy(template.policy_json as unknown as PolicyDefinitionType);
      setValidation(null);
      setActiveTab("generate");
    },
    [],
  );

  const handleTabSelect = useCallback(
    (_: unknown, data: { value: string }) => {
      setActiveTab(data.value);
      if (data.value === "library") {
        handleLoadLibrary();
      }
    },
    [handleLoadLibrary],
  );

  return (
    <div className={styles.container} data-testid="policy-creator">
      <Text as="h2" size={600} weight="semibold">
        Policy Creator
      </Text>

      <TabList selectedValue={activeTab} onTabSelect={handleTabSelect}>
        <Tab value="generate">Generate Policy</Tab>
        <Tab value="library">Policy Library</Tab>
      </TabList>

      {activeTab === "generate" && (
        <div className={styles.inputSection}>
          <Text className={styles.label}>Describe your governance rule in plain English</Text>
          <Textarea
            placeholder="e.g., Deny creation of public IP addresses in production subscriptions"
            value={description}
            onChange={(_e, data) => setDescription(data.value)}
            rows={3}
            data-testid="policy-description-input"
          />
          <div className={styles.buttonRow}>
            <Button
              appearance="primary"
              onClick={handleGenerate}
              disabled={loading || !description.trim()}
              data-testid="generate-policy-btn"
            >
              {loading ? "Generating..." : "Generate Policy"}
            </Button>
            {generatedPolicy && (
              <Button
                appearance="secondary"
                onClick={handleApply}
                disabled={loading}
                data-testid="apply-policy-btn"
              >
                Add to Architecture
              </Button>
            )}
          </div>

          {error && (
            <Text className={styles.errorText} data-testid="policy-error">
              {error}
            </Text>
          )}

          {validation && (
            <div className={styles.validationRow} data-testid="validation-status">
              {validation.valid ? (
                <Badge color="success" appearance="filled">
                  Valid
                </Badge>
              ) : (
                <Badge color="danger" appearance="filled">
                  Invalid
                </Badge>
              )}
              {validation.warnings.length > 0 && (
                <Badge color="warning" appearance="filled">
                  {validation.warnings.length} warning{validation.warnings.length > 1 ? "s" : ""}
                </Badge>
              )}
            </div>
          )}

          {generatedPolicy && (
            <Card className={styles.previewCard} data-testid="policy-preview">
              <CardHeader
                header={
                  <Text weight="semibold">
                    {generatedPolicy.display_name || generatedPolicy.name || "Generated Policy"}
                  </Text>
                }
              />
              <pre className={styles.codeBlock} data-testid="policy-json">
                {JSON.stringify(generatedPolicy, null, 2)}
              </pre>
            </Card>
          )}
        </div>
      )}

      {activeTab === "library" && (
        <div className={styles.templateList} data-testid="policy-library">
          {templates.length === 0 && !loading && (
            <Text>No templates available.</Text>
          )}
          {templates.map((template) => (
            <Card
              key={template.id}
              className={styles.templateCard}
              data-testid={`template-${template.id}`}
            >
              <CardHeader
                header={<Text weight="semibold">{template.name}</Text>}
                description={template.description}
                action={
                  <Button
                    size="small"
                    appearance="primary"
                    onClick={() => handleSelectTemplate(template)}
                    data-testid={`use-template-${template.id}`}
                  >
                    Use Template
                  </Button>
                }
              />
              <Badge appearance="outline">{template.category}</Badge>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
