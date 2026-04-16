import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import ChatMessage from "./ChatMessage";

function renderWithTheme(ui: React.ReactElement) {
  return render(<FluentProvider theme={teamsLightTheme}>{ui}</FluentProvider>);
}

describe("ChatMessage", () => {
  it("renders user message with correct test id", () => {
    renderWithTheme(
      <ChatMessage role="user" content="Hello world" />,
    );
    expect(screen.getByTestId("chat-message-user")).toBeInTheDocument();
  });

  it("renders assistant message with correct test id", () => {
    renderWithTheme(
      <ChatMessage role="assistant" content="Hi there!" />,
    );
    expect(screen.getByTestId("chat-message-assistant")).toBeInTheDocument();
  });

  it("displays message content", () => {
    renderWithTheme(
      <ChatMessage role="user" content="Test message content" />,
    );
    expect(screen.getByText("Test message content")).toBeInTheDocument();
  });

  it("renders bold markdown text", () => {
    renderWithTheme(
      <ChatMessage role="assistant" content="Use **Azure Firewall** for this" />,
    );
    expect(screen.getByText("Azure Firewall")).toBeInTheDocument();
    const bold = screen.getByText("Azure Firewall");
    expect(bold.tagName).toBe("STRONG");
  });

  it("renders inline code", () => {
    renderWithTheme(
      <ChatMessage role="assistant" content="Run `az login` to start" />,
    );
    expect(screen.getByText("az login")).toBeInTheDocument();
    const code = screen.getByText("az login");
    expect(code.tagName).toBe("CODE");
  });

  it("renders list items as bullet points", () => {
    renderWithTheme(
      <ChatMessage role="assistant" content="- Item one\n- Item two" />,
    );
    expect(screen.getByText(/Item one/)).toBeInTheDocument();
    expect(screen.getByText(/Item two/)).toBeInTheDocument();
  });

  it("shows timestamp when provided", () => {
    const timestamp = "2025-01-15T10:30:00Z";
    renderWithTheme(
      <ChatMessage role="user" content="Hello" timestamp={timestamp} />,
    );
    // Timestamp should render a time string
    const timeStr = new Date(timestamp).toLocaleTimeString();
    expect(screen.getByText(timeStr)).toBeInTheDocument();
  });

  it("does not show avatar for user messages", () => {
    renderWithTheme(
      <ChatMessage role="user" content="User message" />,
    );
    expect(screen.queryByLabelText("AI assistant")).not.toBeInTheDocument();
  });

  it("shows avatar for assistant messages", () => {
    renderWithTheme(
      <ChatMessage role="assistant" content="AI response" />,
    );
    // The Avatar element has role="img" with aria-label
    expect(screen.getByRole("img", { name: "AI assistant" })).toBeInTheDocument();
  });
});
