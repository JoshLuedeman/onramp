import { useState, useRef, useEffect } from "react";
import {
  makeStyles,
  tokens,
  Card,
  Input,
  Button,
  Body1,
  Caption1,
  Spinner,
} from "@fluentui/react-components";
import {
  SendRegular,
  ChevronUpRegular,
  ChevronDownRegular,
  CheckmarkRegular,
} from "@fluentui/react-icons";
import type { Architecture } from "../../services/api";
import { api } from "../../services/api";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  updatedArchitecture?: Record<string, unknown> | null;
  applied?: boolean;
}

interface ArchitectureChatProps {
  architecture: Architecture;
  onArchitectureUpdate: (arch: Architecture) => void;
}

const SUGGESTED_PROMPTS = [
  "Why did you choose this network topology?",
  "Add more security controls",
  "Reduce estimated costs",
  "Explain the management group hierarchy",
];

const useStyles = makeStyles({
  wrapper: {
    marginTop: "24px",
  },
  toggleButton: {
    width: "100%",
    justifyContent: "space-between",
  },
  chatPanel: {
    padding: "16px",
    marginTop: "4px",
  },
  messages: {
    maxHeight: "300px",
    overflowY: "auto",
    display: "flex",
    flexDirection: "column",
    gap: "8px",
    marginBottom: "12px",
  },
  userMessage: {
    alignSelf: "flex-end",
    backgroundColor: tokens.colorBrandBackground,
    color: tokens.colorNeutralForegroundOnBrand,
    padding: "8px 12px",
    borderRadius: "12px 12px 2px 12px",
    maxWidth: "80%",
  },
  assistantMessage: {
    alignSelf: "flex-start",
    backgroundColor: tokens.colorNeutralBackground3,
    padding: "8px 12px",
    borderRadius: "12px 12px 12px 2px",
    maxWidth: "80%",
  },
  inputRow: {
    display: "flex",
    gap: "8px",
  },
  input: {
    flexGrow: 1,
  },
  chips: {
    display: "flex",
    flexWrap: "wrap",
    gap: "6px",
    marginBottom: "12px",
  },
  chip: {
    fontSize: tokens.fontSizeBase200,
  },
  applyButton: {
    marginTop: "6px",
  },
});

export default function ArchitectureChat({
  architecture,
  onArchitectureUpdate,
}: ArchitectureChatProps) {
  const styles = useStyles();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const userMsg: ChatMessage = { role: "user", content: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const result = await api.architecture.refine(
        architecture as Record<string, unknown>,
        trimmed,
      );
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: result.response,
        updatedArchitecture: result.updated_architecture,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const applyChanges = (msg: ChatMessage) => {
    if (!msg.updatedArchitecture) return;
    onArchitectureUpdate(msg.updatedArchitecture as Architecture);
    setMessages((prev) =>
      prev.map((m) => (m === msg ? { ...m, applied: true } : m)),
    );
  };

  return (
    <div className={styles.wrapper}>
      <Button
        appearance="subtle"
        className={styles.toggleButton}
        icon={open ? <ChevronDownRegular /> : <ChevronUpRegular />}
        iconPosition="after"
        onClick={() => setOpen((v) => !v)}
      >
        💬 Refine with AI Chat
      </Button>

      {open && (
        <Card className={styles.chatPanel}>
          {messages.length === 0 && (
            <>
              <Caption1>Ask a question or request changes to your architecture:</Caption1>
              <div className={styles.chips}>
                {SUGGESTED_PROMPTS.map((prompt) => (
                  <Button
                    key={prompt}
                    appearance="outline"
                    size="small"
                    className={styles.chip}
                    onClick={() => sendMessage(prompt)}
                  >
                    {prompt}
                  </Button>
                ))}
              </div>
            </>
          )}

          {messages.length > 0 && (
            <div className={styles.messages}>
              {messages.map((msg, i) => (
                <div key={i}>
                  <div
                    className={
                      msg.role === "user"
                        ? styles.userMessage
                        : styles.assistantMessage
                    }
                  >
                    <Body1>{msg.content}</Body1>
                  </div>
                  {msg.role === "assistant" &&
                    msg.updatedArchitecture &&
                    !msg.applied && (
                      <Button
                        appearance="primary"
                        size="small"
                        icon={<CheckmarkRegular />}
                        className={styles.applyButton}
                        onClick={() => applyChanges(msg)}
                      >
                        Apply Changes
                      </Button>
                    )}
                  {msg.applied && (
                    <Caption1>✅ Changes applied</Caption1>
                  )}
                </div>
              ))}
              {loading && <Spinner size="tiny" label="Thinking..." />}
              <div ref={messagesEndRef} />
            </div>
          )}

          <div className={styles.inputRow}>
            <Input
              className={styles.input}
              placeholder="Ask about or refine your architecture..."
              value={input}
              onChange={(_e, data) => setInput(data.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") sendMessage(input);
              }}
              disabled={loading}
            />
            <Button
              appearance="primary"
              icon={<SendRegular />}
              onClick={() => sendMessage(input)}
              disabled={loading || !input.trim()}
            >
              Send
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
