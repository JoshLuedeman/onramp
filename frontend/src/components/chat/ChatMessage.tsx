import {
  makeStyles,
  tokens,
  Text,
  Avatar,
} from "@fluentui/react-components";
import { BotRegular } from "@fluentui/react-icons";

export interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
}

const useStyles = makeStyles({
  wrapper: {
    display: "flex",
    gap: tokens.spacingHorizontalM,
    padding: `${tokens.spacingVerticalS} ${tokens.spacingHorizontalM}`,
    maxWidth: "100%",
  },
  wrapperUser: {
    flexDirection: "row-reverse",
  },
  wrapperAssistant: {
    flexDirection: "row",
  },
  bubble: {
    maxWidth: "70%",
    padding: `${tokens.spacingVerticalS} ${tokens.spacingHorizontalM}`,
    borderRadius: tokens.borderRadiusMedium,
    wordBreak: "break-word",
    whiteSpace: "pre-wrap",
  },
  bubbleUser: {
    backgroundColor: tokens.colorBrandBackground,
    color: tokens.colorNeutralForegroundOnBrand,
  },
  bubbleAssistant: {
    backgroundColor: tokens.colorNeutralBackground3,
    color: tokens.colorNeutralForeground1,
  },
  timestamp: {
    display: "block",
    marginTop: tokens.spacingVerticalXS,
    fontSize: tokens.fontSizeBase100,
    opacity: 0.7,
  },
  codeBlock: {
    backgroundColor: tokens.colorNeutralBackground4,
    padding: tokens.spacingVerticalXS,
    borderRadius: tokens.borderRadiusSmall,
    fontFamily: tokens.fontFamilyMonospace,
    fontSize: tokens.fontSizeBase200,
    overflowX: "auto",
    display: "block",
    marginTop: tokens.spacingVerticalXS,
    marginBottom: tokens.spacingVerticalXS,
  },
  inlineCode: {
    backgroundColor: tokens.colorNeutralBackground4,
    padding: `0 ${tokens.spacingHorizontalXS}`,
    borderRadius: tokens.borderRadiusSmall,
    fontFamily: tokens.fontFamilyMonospace,
    fontSize: tokens.fontSizeBase200,
  },
  blockSpan: {
    display: "block",
  },
});

/** Render simple markdown: **bold**, `code`, ```code blocks```, and - lists. */
function renderMarkdown(text: string, styles: ReturnType<typeof useStyles>) {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Code block
    if (line.startsWith("```")) {
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing ```
      elements.push(
        <code key={`code-${i}`} className={styles.codeBlock}>
          {codeLines.join("\n")}
        </code>,
      );
      continue;
    }

    // List item
    if (line.startsWith("- ") || line.startsWith("* ")) {
      elements.push(
        <span key={`li-${i}`} className={styles.blockSpan}>
          {"• "}{renderInline(line.slice(2), styles)}
        </span>,
      );
      i++;
      continue;
    }

    // Regular paragraph
    elements.push(
      <span key={`p-${i}`} className={styles.blockSpan}>
        {renderInline(line, styles)}
      </span>,
    );
    i++;
  }

  return elements;
}

/** Render inline formatting: **bold** and `inline code`. */
function renderInline(text: string, styles: ReturnType<typeof useStyles>) {
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*(.+?)\*\*|`([^`]+)`)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    if (match[2]) {
      parts.push(<strong key={`b-${match.index}`}>{match[2]}</strong>);
    } else if (match[3]) {
      parts.push(
        <code key={`ic-${match.index}`} className={styles.inlineCode}>
          {match[3]}
        </code>,
      );
    }
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  return parts;
}

export default function ChatMessage({ role, content, timestamp }: ChatMessageProps) {
  const styles = useStyles();
  const isUser = role === "user";

  const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString() : undefined;
  const ariaLabel = `${isUser ? "You" : "AI assistant"}, message${timeStr ? ` at ${timeStr}` : ""}`;

  return (
    <div
      className={`${styles.wrapper} ${isUser ? styles.wrapperUser : styles.wrapperAssistant}`}
      data-testid={`chat-message-${role}`}
      role="article"
      aria-label={ariaLabel}
      tabIndex={0}
    >
      {!isUser && (
        <Avatar
          icon={<BotRegular />}
          color="brand"
          size={28}
          aria-label="AI assistant"
        />
      )}
      <div className={`${styles.bubble} ${isUser ? styles.bubbleUser : styles.bubbleAssistant}`}>
        <Text>{renderMarkdown(content, styles)}</Text>
        {timestamp && (
          <Text className={styles.timestamp}>
            {timeStr}
          </Text>
        )}
      </div>
    </div>
  );
}
