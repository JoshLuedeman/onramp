import { useState, useEffect, useCallback, useRef } from "react";
import { useParams } from "react-router-dom";
import {
  makeStyles,
  tokens,
  Title2,
  Body1,
  Button,
  Card,
  Spinner,
  Text,
} from "@fluentui/react-components";
import {
  AddRegular,
  ChatRegular,
  DeleteRegular,
  ArchiveRegular,
} from "@fluentui/react-icons";
import { api } from "../services/api";
import type {
  ConversationResponse,
  ConversationMessageItem,
} from "../services/api";
import ChatMessage from "../components/chat/ChatMessage";
import ChatInput from "../components/chat/ChatInput";
import SuggestedPrompts from "../components/chat/SuggestedPrompts";

const useStyles = makeStyles({
  root: {
    display: "flex",
    height: "calc(100vh - 60px)",
    overflow: "hidden",
  },
  sidebar: {
    width: "280px",
    minWidth: "280px",
    borderRight: `1px solid ${tokens.colorNeutralStroke1}`,
    display: "flex",
    flexDirection: "column",
    backgroundColor: tokens.colorNeutralBackground2,
  },
  sidebarHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: tokens.spacingVerticalM,
    borderBottom: `1px solid ${tokens.colorNeutralStroke1}`,
  },
  conversationList: {
    flexGrow: 1,
    overflowY: "auto",
    padding: tokens.spacingVerticalS,
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalXS,
  },
  conversationItem: {
    padding: `${tokens.spacingVerticalS} ${tokens.spacingHorizontalM}`,
    borderRadius: tokens.borderRadiusMedium,
    cursor: "pointer",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    ":hover": {
      backgroundColor: tokens.colorNeutralBackground1Hover,
    },
  },
  conversationItemActive: {
    backgroundColor: tokens.colorNeutralBackground1Selected,
  },
  conversationInfo: {
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    flexGrow: 1,
  },
  chatArea: {
    flexGrow: 1,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  messageList: {
    flexGrow: 1,
    overflowY: "auto",
    padding: `${tokens.spacingVerticalM} ${tokens.spacingHorizontalL}`,
    display: "flex",
    flexDirection: "column",
    gap: tokens.spacingVerticalS,
  },
  loadingContainer: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
    padding: `${tokens.spacingVerticalS} ${tokens.spacingHorizontalM}`,
  },
  emptyState: {
    flexGrow: 1,
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
  },
  actionButtons: {
    display: "flex",
    gap: tokens.spacingHorizontalXS,
  },
  srOnly: {
    position: "absolute",
    width: "1px",
    height: "1px",
    padding: "0",
    margin: "-1px",
    overflow: "hidden",
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    clip: "rect(0, 0, 0, 0)" as any,
    whiteSpace: "nowrap",
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    borderWidth: "0" as any,
  },
});

export default function ChatPage() {
  const styles = useStyles();
  const { projectId } = useParams<{ projectId: string }>();

  const [conversations, setConversations] = useState<ConversationResponse[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ConversationMessageItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamingStatus, setStreamingStatus] = useState<string>("");
  const messageListRef = useRef<HTMLDivElement>(null);
  const chatInputRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom on new messages while preserving focus on input
  useEffect(() => {
    if (messageListRef.current) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
    }
  }, [messages]);

  // Load conversation list
  const loadConversations = useCallback(async () => {
    try {
      const convos = await api.chat.getConversations(projectId);
      setConversations(convos);
    } catch {
      // Silently handle — sidebar may be empty
    }
  }, [projectId]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // Load conversation messages when active conversation changes
  useEffect(() => {
    if (!activeConversationId) return;

    const loadMessages = async () => {
      setLoading(true);
      try {
        const conv = await api.chat.getConversation(activeConversationId);
        setMessages(
          conv.messages.filter((m: ConversationMessageItem) => m.role !== "system"),
        );
      } catch {
        setError("Failed to load conversation.");
      } finally {
        setLoading(false);
      }
    };

    loadMessages();
  }, [activeConversationId]);

  const handleNewConversation = useCallback(async () => {
    try {
      const conv = await api.chat.createConversation(projectId);
      setConversations((prev) => [conv, ...prev]);
      setActiveConversationId(conv.id);
      setMessages([]);
      setError(null);
    } catch {
      setError("Failed to create conversation.");
    }
  }, [projectId]);

  const handleSendMessage = useCallback(
    async (content: string) => {
      let conversationId = activeConversationId;

      // Auto-create conversation if none active
      if (!conversationId) {
        try {
          const conv = await api.chat.createConversation(projectId);
          setConversations((prev) => [conv, ...prev]);
          setActiveConversationId(conv.id);
          conversationId = conv.id;
        } catch {
          setError("Failed to create conversation.");
          return;
        }
      }

      // Optimistically add user message
      const userMsg: ConversationMessageItem = {
        id: `temp-${Date.now()}`,
        role: "user",
        content,
        token_count: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setSending(true);
      setError(null);
      setStreamingStatus("AI is thinking…");

      try {
        const response = await api.chat.sendMessage(conversationId, content);
        setMessages((prev) => [...prev, response.assistant_message]);
        setStreamingStatus("Response complete");
        // Clear the status after announcement
        setTimeout(() => setStreamingStatus(""), 1000);
      } catch {
        setError("Failed to send message. Please try again.");
        setStreamingStatus("");
      } finally {
        setSending(false);
      }
    },
    [activeConversationId, projectId],
  );

  const handleSelectConversation = useCallback((id: string) => {
    setActiveConversationId(id);
    setError(null);
  }, []);

  const handleArchiveConversation = useCallback(
    async (id: string) => {
      try {
        await api.chat.archiveConversation(id);
        setConversations((prev) => prev.filter((c) => c.id !== id));
        if (activeConversationId === id) {
          setActiveConversationId(null);
          setMessages([]);
        }
      } catch {
        setError("Failed to archive conversation.");
      }
    },
    [activeConversationId],
  );

  const handleDeleteConversation = useCallback(
    async (id: string) => {
      try {
        await api.chat.deleteConversation(id);
        setConversations((prev) => prev.filter((c) => c.id !== id));
        if (activeConversationId === id) {
          setActiveConversationId(null);
          setMessages([]);
        }
      } catch {
        setError("Failed to delete conversation.");
      }
    },
    [activeConversationId],
  );

  const handleSuggestedPrompt = useCallback(
    (prompt: string) => {
      handleSendMessage(prompt);
    },
    [handleSendMessage],
  );

  const visibleMessages = messages.filter((m) => m.role !== "system");
  const showSuggestedPrompts = !activeConversationId || visibleMessages.length === 0;

  return (
    <div className={styles.root}>
      {/* Sidebar */}
      <div className={styles.sidebar} data-testid="conversation-sidebar">
        <div className={styles.sidebarHeader}>
          <Title2>Chats</Title2>
          <Button
            appearance="subtle"
            icon={<AddRegular />}
            onClick={handleNewConversation}
            aria-label="New conversation"
          />
        </div>
        <div className={styles.conversationList} data-testid="conversation-list">
          {conversations.map((conv) => (
            <Card
              key={conv.id}
              className={`${styles.conversationItem} ${
                conv.id === activeConversationId ? styles.conversationItemActive : ""
              }`}
              onClick={() => handleSelectConversation(conv.id)}
            >
              <div className={styles.conversationInfo}>
                <Text weight="semibold" size={200}>
                  {conv.title ?? "New conversation"}
                </Text>
              </div>
              <div className={styles.actionButtons}>
                <Button
                  appearance="subtle"
                  icon={<ArchiveRegular />}
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleArchiveConversation(conv.id);
                  }}
                  aria-label="Archive conversation"
                />
                <Button
                  appearance="subtle"
                  icon={<DeleteRegular />}
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteConversation(conv.id);
                  }}
                  aria-label="Delete conversation"
                />
              </div>
            </Card>
          ))}
          {conversations.length === 0 && (
            <Body1 style={{ padding: tokens.spacingVerticalM, textAlign: "center", color: tokens.colorNeutralForeground3 }}>
              No conversations yet
            </Body1>
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className={styles.chatArea} data-testid="chat-area" role="region" aria-label="Chat conversation">
        {showSuggestedPrompts && !loading ? (
          <div className={styles.emptyState}>
            <ChatRegular style={{ fontSize: "48px", color: tokens.colorBrandForeground1, marginBottom: tokens.spacingVerticalM }} />
            <Title2>AI Architect Chat</Title2>
            <Body1 style={{ color: tokens.colorNeutralForeground3, marginBottom: tokens.spacingVerticalL }}>
              Ask questions about your Azure architecture
            </Body1>
            <SuggestedPrompts onSelect={handleSuggestedPrompt} />
          </div>
        ) : (
          <div
            className={styles.messageList}
            ref={messageListRef}
            data-testid="message-list"
            role="log"
            aria-label="Chat messages"
            aria-live="polite"
            aria-relevant="additions"
          >
            {loading ? (
              <div className={styles.loadingContainer} role="status">
                <Spinner size="tiny" />
                <Text>Loading messages...</Text>
              </div>
            ) : (
              visibleMessages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  role={msg.role as "user" | "assistant"}
                  content={msg.content}
                  timestamp={msg.created_at}
                />
              ))
            )}
            {sending && (
              <div className={styles.loadingContainer} data-testid="sending-indicator" role="status">
                <Spinner size="tiny" />
                <Text>AI is thinking...</Text>
              </div>
            )}
          </div>
        )}

        {/* Screen reader announcements for streaming states */}
        <div
          aria-live="assertive"
          aria-atomic="true"
          className={styles.srOnly}
          data-testid="sr-streaming-status"
        >
          {streamingStatus}
        </div>

        {error && (
          <Text
            style={{ padding: tokens.spacingVerticalS, color: tokens.colorPaletteRedForeground1, textAlign: "center" }}
            data-testid="chat-error"
            role="alert"
          >
            {error}
          </Text>
        )}
        <div ref={chatInputRef}>
          <ChatInput onSend={handleSendMessage} disabled={sending} />
        </div>
      </div>
    </div>
  );
}
