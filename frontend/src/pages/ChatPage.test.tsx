import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ChatPage from "./ChatPage";

// Mock the API module
vi.mock("../services/api", () => ({
  api: {
    chat: {
      createConversation: vi.fn(),
      getConversations: vi.fn(),
      getConversation: vi.fn(),
      sendMessage: vi.fn(),
      archiveConversation: vi.fn(),
      deleteConversation: vi.fn(),
    },
  },
}));

import { api } from "../services/api";

const mockApi = api as {
  chat: {
    createConversation: ReturnType<typeof vi.fn>;
    getConversations: ReturnType<typeof vi.fn>;
    getConversation: ReturnType<typeof vi.fn>;
    sendMessage: ReturnType<typeof vi.fn>;
    archiveConversation: ReturnType<typeof vi.fn>;
    deleteConversation: ReturnType<typeof vi.fn>;
  };
};

function renderChatPage(route = "/chat") {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/projects/:projectId/chat" element={<ChatPage />} />
        </Routes>
      </MemoryRouter>
    </FluentProvider>,
  );
}

describe("ChatPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApi.chat.getConversations.mockResolvedValue([]);
  });

  it("renders the chat page with sidebar and chat area", async () => {
    renderChatPage();
    await waitFor(() => {
      expect(screen.getByTestId("conversation-sidebar")).toBeInTheDocument();
      expect(screen.getByTestId("chat-area")).toBeInTheDocument();
    });
  });

  it("shows suggested prompts for empty state", async () => {
    renderChatPage();
    await waitFor(() => {
      expect(screen.getByTestId("suggested-prompts")).toBeInTheDocument();
    });
  });

  it("displays AI Architect Chat title in empty state", async () => {
    renderChatPage();
    await waitFor(() => {
      expect(screen.getByText("AI Architect Chat")).toBeInTheDocument();
    });
  });

  it("shows 'No conversations yet' when list is empty", async () => {
    renderChatPage();
    await waitFor(() => {
      expect(screen.getByText("No conversations yet")).toBeInTheDocument();
    });
  });

  it("renders the chat input", async () => {
    renderChatPage();
    await waitFor(() => {
      expect(screen.getByTestId("chat-input")).toBeInTheDocument();
    });
  });

  it("shows conversation list when conversations exist", async () => {
    mockApi.chat.getConversations.mockResolvedValue([
      {
        id: "conv-1",
        title: "Security Discussion",
        status: "active",
        model_name: "gpt-4o",
        total_tokens: 100,
        project_id: "proj-1",
        created_at: "2025-01-01T00:00:00Z",
        updated_at: "2025-01-01T00:00:00Z",
        message_count: 3,
      },
    ]);

    renderChatPage();
    await waitFor(() => {
      expect(screen.getByText("Security Discussion")).toBeInTheDocument();
    });
  });

  it("creates a new conversation when new button is clicked", async () => {
    const user = userEvent.setup();
    mockApi.chat.createConversation.mockResolvedValue({
      id: "new-conv",
      title: "New conversation",
      status: "active",
      model_name: "gpt-4o",
      total_tokens: 0,
      project_id: "default",
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
      message_count: 0,
    });

    renderChatPage();
    await waitFor(() => {
      expect(screen.getByLabelText("New conversation")).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText("New conversation"));
    expect(mockApi.chat.createConversation).toHaveBeenCalled();
  });

  it("sends a message when clicking a suggested prompt", async () => {
    const user = userEvent.setup();
    mockApi.chat.createConversation.mockResolvedValue({
      id: "auto-conv",
      title: "New conversation",
      status: "active",
      model_name: "gpt-4o",
      total_tokens: 0,
      project_id: "default",
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
      message_count: 0,
    });
    mockApi.chat.sendMessage.mockResolvedValue({
      assistant_message: {
        id: "msg-1",
        role: "assistant",
        content: "Here is my DR recommendation...",
        token_count: 50,
        created_at: "2025-01-01T00:00:01Z",
      },
      conversation: {
        id: "auto-conv",
        title: "New conversation",
        status: "active",
        model_name: "gpt-4o",
        total_tokens: 80,
        project_id: "default",
        created_at: "2025-01-01T00:00:00Z",
        updated_at: "2025-01-01T00:00:01Z",
        message_count: 2,
      },
    });

    renderChatPage();
    await waitFor(() => {
      expect(screen.getByLabelText("Add disaster recovery")).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText("Add disaster recovery"));

    await waitFor(() => {
      expect(mockApi.chat.sendMessage).toHaveBeenCalledWith("auto-conv", "Add disaster recovery");
    });
  });

  it("displays messages from a loaded conversation", async () => {
    mockApi.chat.getConversations.mockResolvedValue([
      {
        id: "conv-1",
        title: "My Chat",
        status: "active",
        model_name: "gpt-4o",
        total_tokens: 200,
        project_id: "default",
        created_at: "2025-01-01T00:00:00Z",
        updated_at: "2025-01-01T00:00:00Z",
        message_count: 2,
      },
    ]);
    mockApi.chat.getConversation.mockResolvedValue({
      id: "conv-1",
      title: "My Chat",
      status: "active",
      model_name: "gpt-4o",
      total_tokens: 200,
      project_id: "default",
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
      message_count: 2,
      messages: [
        { id: "m1", role: "system", content: "You are an AI.", token_count: 10, created_at: "2025-01-01T00:00:00Z" },
        { id: "m2", role: "user", content: "Optimize my costs", token_count: 5, created_at: "2025-01-01T00:00:01Z" },
        { id: "m3", role: "assistant", content: "Consider reserved instances.", token_count: 10, created_at: "2025-01-01T00:00:02Z" },
      ],
    });

    const user = userEvent.setup();
    renderChatPage();

    await waitFor(() => {
      expect(screen.getByText("My Chat")).toBeInTheDocument();
    });

    await user.click(screen.getByText("My Chat"));

    await waitFor(() => {
      expect(screen.getByText("Optimize my costs")).toBeInTheDocument();
      expect(screen.getByText("Consider reserved instances.")).toBeInTheDocument();
    });
  });

  it("shows loading indicator while waiting for AI response", async () => {
    const user = userEvent.setup();

    // Never resolve to keep "sending" state
    mockApi.chat.createConversation.mockResolvedValue({
      id: "conv-pending",
      title: "New conversation",
      status: "active",
      model_name: "gpt-4o",
      total_tokens: 0,
      project_id: "default",
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
      message_count: 0,
    });
    mockApi.chat.sendMessage.mockReturnValue(new Promise(() => {})); // Never resolves

    renderChatPage();
    await waitFor(() => {
      expect(screen.getByLabelText("Chat message input")).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText("Chat message input"), "Hello");
    await user.click(screen.getByLabelText("Send message"));

    await waitFor(() => {
      expect(screen.getByTestId("sending-indicator")).toBeInTheDocument();
      expect(screen.getByText("AI is thinking...")).toBeInTheDocument();
    });
  });

  it("handles send message error gracefully", async () => {
    const user = userEvent.setup();
    mockApi.chat.createConversation.mockResolvedValue({
      id: "conv-err",
      title: "New conversation",
      status: "active",
      model_name: "gpt-4o",
      total_tokens: 0,
      project_id: "default",
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
      message_count: 0,
    });
    mockApi.chat.sendMessage.mockRejectedValue(new Error("Network error"));

    renderChatPage();
    await waitFor(() => {
      expect(screen.getByLabelText("Chat message input")).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText("Chat message input"), "Test error");
    await user.click(screen.getByLabelText("Send message"));

    await waitFor(() => {
      expect(screen.getByTestId("chat-error")).toBeInTheDocument();
      expect(screen.getByText(/Failed to send message/)).toBeInTheDocument();
    });
  });

  it("renders Chats title in sidebar", async () => {
    renderChatPage();
    await waitFor(() => {
      expect(screen.getByText("Chats")).toBeInTheDocument();
    });
  });
});
