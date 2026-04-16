import { useState, useCallback, type KeyboardEvent } from "react";
import {
  makeStyles,
  tokens,
  Input,
  Button,
} from "@fluentui/react-components";
import { SendRegular } from "@fluentui/react-icons";

export interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

const useStyles = makeStyles({
  container: {
    display: "flex",
    gap: tokens.spacingHorizontalS,
    padding: tokens.spacingVerticalM,
    borderTop: `1px solid ${tokens.colorNeutralStroke1}`,
    backgroundColor: tokens.colorNeutralBackground1,
    alignItems: "flex-end",
  },
  input: {
    flexGrow: 1,
  },
});

export default function ChatInput({ onSend, disabled = false, placeholder }: ChatInputProps) {
  const styles = useStyles();
  const [value, setValue] = useState("");

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (trimmed && !disabled) {
      onSend(trimmed);
      setValue("");
    }
  }, [value, disabled, onSend]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  return (
    <div className={styles.container} data-testid="chat-input">
      <Input
        className={styles.input}
        value={value}
        onChange={(_e, data) => setValue(data.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder ?? "Ask the AI architect..."}
        disabled={disabled}
        aria-label="Chat message input"
      />
      <Button
        appearance="primary"
        icon={<SendRegular />}
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        aria-label="Send message"
      >
        Send
      </Button>
    </div>
  );
}
