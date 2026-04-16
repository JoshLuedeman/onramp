import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import ChatInput from "./ChatInput";

function renderWithTheme(ui: React.ReactElement) {
  return render(<FluentProvider theme={teamsLightTheme}>{ui}</FluentProvider>);
}

describe("ChatInput", () => {
  it("renders input and send button", () => {
    renderWithTheme(<ChatInput onSend={vi.fn()} />);
    expect(screen.getByLabelText("Type a message")).toBeInTheDocument();
    expect(screen.getByLabelText("Send message")).toBeInTheDocument();
  });

  it("send button is disabled when input is empty", () => {
    renderWithTheme(<ChatInput onSend={vi.fn()} />);
    expect(screen.getByLabelText("Send message")).toBeDisabled();
  });

  it("send button is enabled when input has text", async () => {
    const user = userEvent.setup();
    renderWithTheme(<ChatInput onSend={vi.fn()} />);

    await user.type(screen.getByLabelText("Type a message"), "Hello");
    expect(screen.getByLabelText("Send message")).toBeEnabled();
  });

  it("calls onSend when send button is clicked", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    renderWithTheme(<ChatInput onSend={onSend} />);

    await user.type(screen.getByLabelText("Type a message"), "Test message");
    await user.click(screen.getByLabelText("Send message"));

    expect(onSend).toHaveBeenCalledWith("Test message");
  });

  it("clears input after sending", async () => {
    const user = userEvent.setup();
    renderWithTheme(<ChatInput onSend={vi.fn()} />);

    const input = screen.getByLabelText("Type a message");
    await user.type(input, "Test message");
    await user.click(screen.getByLabelText("Send message"));

    expect(input).toHaveValue("");
  });

  it("sends message on Enter key", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    renderWithTheme(<ChatInput onSend={onSend} />);

    await user.type(screen.getByLabelText("Type a message"), "Enter test{enter}");
    expect(onSend).toHaveBeenCalledWith("Enter test");
  });

  it("is disabled when disabled prop is true", () => {
    renderWithTheme(<ChatInput onSend={vi.fn()} disabled />);
    expect(screen.getByLabelText("Type a message")).toBeDisabled();
    expect(screen.getByLabelText("Send message")).toBeDisabled();
  });

  it("shows custom placeholder", () => {
    renderWithTheme(<ChatInput onSend={vi.fn()} placeholder="Type here..." />);
    expect(screen.getByPlaceholderText("Type here...")).toBeInTheDocument();
  });

  it("does not send whitespace-only messages", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    renderWithTheme(<ChatInput onSend={onSend} />);

    await user.type(screen.getByLabelText("Type a message"), "   ");
    expect(screen.getByLabelText("Send message")).toBeDisabled();
  });
});
