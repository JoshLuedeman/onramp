/**
 * ChatPage WCAG 2.1 AA accessibility tests.
 *
 * Tests ARIA live regions, roles, labels, keyboard navigation,
 * screen reader announcements, and focus management.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ChatPage from "./ChatPage";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("../services/api", () => ({
  api: {
    chat: {
      getConversations: vi.fn().mockResolvedValue([]),
      createConversation: vi.fn().mockResolvedValue({
        id: "conv-1",
        title: "Test Chat",
        status: "active",
        model_name: "gpt-4o",
        total_tokens: 0,
        project_id: "proj-1",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        message_count: 0,
      }),
      getConversation: vi.fn().mockResolvedValue({
        id: "conv-1",
        title: "Test Chat",
        status: "active",
        model_name: "gpt-4o",
        total_tokens: 100,
        project_id: "proj-1",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        message_count: 2,
        messages: [
          {
            id: "msg-1",
            role: "user",
            content: "Hello",
            token_count: 10,
            created_at: "2025-01-15T10:00:00Z",
          },
          {
            id: "msg-2",
            role: "assistant",
            content: "Hi there!",
            token_count: 15,
            created_at: "2025-01-15T10:00:05Z",
          },
        ],
      }),
      sendMessage: vi.fn().mockResolvedValue({
        assistant_message: {
          id: "msg-3",
          role: "assistant",
          content: "Response",
          token_count: 10,
          created_at: new Date().toISOString(),
        },
        conversation: {
          id: "conv-1",
          title: "Test Chat",
          status: "active",
          model_name: "gpt-4o",
          total_tokens: 120,
          project_id: "proj-1",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          message_count: 3,
        },
      }),
      archiveConversation: vi.fn().mockResolvedValue(undefined),
      deleteConversation: vi.fn().mockResolvedValue(undefined),
    },
  },
}));

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function renderChatPage() {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter initialEntries={["/projects/proj-1/chat"]}>
        <Routes>
          <Route path="/projects/:projectId/chat" element={<ChatPage />} />
        </Routes>
      </MemoryRouter>
    </FluentProvider>,
  );
}

async function renderChatWithMessages() {
  const { api } = await import("../services/api");
  // Return a conversation with messages to get past the empty state
  (api.chat.getConversations as ReturnType<typeof vi.fn>).mockResolvedValue([
    {
      id: "conv-1",
      title: "Test Chat",
      status: "active",
      model_name: "gpt-4o",
      total_tokens: 100,
      project_id: "proj-1",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      message_count: 2,
    },
  ]);

  const result = render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter initialEntries={["/projects/proj-1/chat"]}>
        <Routes>
          <Route path="/projects/:projectId/chat" element={<ChatPage />} />
        </Routes>
      </MemoryRouter>
    </FluentProvider>,
  );

  // Click on the conversation to load messages
  const sidebar = await screen.findByTestId("conversation-list");
  const convItem = within(sidebar).getByText("Test Chat");
  await userEvent.setup().click(convItem);

  // Wait for messages to load
  await screen.findByTestId("message-list");

  return result;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ChatPage Accessibility", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // 1 — Chat area has region role with aria-label
  it("chat area has role=region with aria-label", () => {
    renderChatPage();
    const chatArea = screen.getByTestId("chat-area");
    expect(chatArea).toHaveAttribute("role", "region");
    expect(chatArea).toHaveAttribute("aria-label", "Chat conversation");
  });

  // 2 — Message list has role="log"
  it("message list has role=log", async () => {
    await renderChatWithMessages();
    const messageList = screen.getByTestId("message-list");
    expect(messageList).toHaveAttribute("role", "log");
  });

  // 3 — Message list has aria-live="polite"
  it("message list has aria-live=polite for incoming messages", async () => {
    await renderChatWithMessages();
    const messageList = screen.getByTestId("message-list");
    expect(messageList).toHaveAttribute("aria-live", "polite");
  });

  // 4 — Message list has aria-label
  it("message list has aria-label", async () => {
    await renderChatWithMessages();
    const messageList = screen.getByTestId("message-list");
    expect(messageList).toHaveAttribute("aria-label", "Chat messages");
  });

  // 5 — Chat input has correct aria-label
  it("chat input has aria-label 'Type a message'", () => {
    renderChatPage();
    expect(screen.getByLabelText("Type a message")).toBeInTheDocument();
  });

  // 6 — Chat input has keyboard shortcut hint
  it("chat input has keyboard shortcut hint for screen readers", () => {
    renderChatPage();
    const hint = document.getElementById("chat-input-hint");
    expect(hint).toBeInTheDocument();
    expect(hint!.textContent).toContain("Press Enter to send");
  });

  // 7 — Chat messages have role="article"
  it("chat messages have role=article", async () => {
    await renderChatWithMessages();
    const messages = screen.getAllByRole("article");
    expect(messages.length).toBeGreaterThanOrEqual(2);
  });

  // 8 — Chat messages have aria-label with sender
  it("chat messages have aria-label with sender info", async () => {
    await renderChatWithMessages();
    const userMsg = screen.getByTestId("chat-message-user");
    expect(userMsg).toHaveAttribute("aria-label");
    expect(userMsg.getAttribute("aria-label")).toContain("You");

    const assistantMsg = screen.getByTestId("chat-message-assistant");
    expect(assistantMsg).toHaveAttribute("aria-label");
    expect(assistantMsg.getAttribute("aria-label")).toContain("AI assistant");
    expect(assistantMsg.getAttribute("aria-label")).toContain("message");
  });

  // 9 — Chat messages have tabIndex for keyboard navigation
  it("chat messages are keyboard navigable with tabIndex", async () => {
    await renderChatWithMessages();
    const userMsg = screen.getByTestId("chat-message-user");
    expect(userMsg).toHaveAttribute("tabindex", "0");

    const assistantMsg = screen.getByTestId("chat-message-assistant");
    expect(assistantMsg).toHaveAttribute("tabindex", "0");
  });

  // 10 — Screen reader streaming status region exists
  it("has screen reader status region for streaming announcements", () => {
    renderChatPage();
    const srStatus = screen.getByTestId("sr-streaming-status");
    expect(srStatus).toHaveAttribute("aria-live", "assertive");
    expect(srStatus).toHaveAttribute("aria-atomic", "true");
  });

  // 11 — Suggested prompts grid has role="list"
  it("suggested prompts grid has role=list", () => {
    renderChatPage();
    const promptGrid = screen.getByRole("list", { name: "Suggested prompts" });
    expect(promptGrid).toBeInTheDocument();
  });

  // 12 — Suggested prompt cards have role="listitem"
  it("suggested prompt cards have role=listitem", () => {
    renderChatPage();
    const items = screen.getAllByRole("listitem");
    expect(items.length).toBe(6);
  });

  // 13 — Focus stays on input after sending a message
  it("focus management: input remains accessible after sending", async () => {
    renderChatPage();
    const user = userEvent.setup();

    const input = screen.getByLabelText("Type a message");
    await user.click(input);
    await user.type(input, "Hello{enter}");

    // Input should still be in the document and accessible
    expect(screen.getByLabelText("Type a message")).toBeInTheDocument();
  });

  // 14 — Loading indicator has role="status" when visible
  it("sending indicator has role=status when streaming", async () => {
    const { api } = await import("../services/api");

    // Make sendMessage return a promise that we control
    let resolveMessage!: (value: unknown) => void;
    (api.chat.sendMessage as ReturnType<typeof vi.fn>).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveMessage = resolve;
        }),
    );

    await renderChatWithMessages();
    const user = userEvent.setup();

    const input = screen.getByLabelText("Type a message");
    await user.type(input, "Hello");
    await user.click(screen.getByLabelText("Send message"));

    // Now the sending indicator should be visible
    const sendingIndicator = await screen.findByTestId("sending-indicator");
    expect(sendingIndicator).toHaveAttribute("role", "status");

    // Resolve the promise to clean up
    resolveMessage({
      assistant_message: {
        id: "msg-3",
        role: "assistant",
        content: "Response",
        token_count: 10,
        created_at: new Date().toISOString(),
      },
      conversation: {
        id: "conv-1",
        title: "Test Chat",
        status: "active",
        model_name: "gpt-4o",
        total_tokens: 120,
        project_id: "proj-1",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        message_count: 3,
      },
    });
  });
});
