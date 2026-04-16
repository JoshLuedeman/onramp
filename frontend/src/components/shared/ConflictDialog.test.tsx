import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import ConflictDialog from "./ConflictDialog";
import type { ConflictResponse } from "../../services/api";

const defaultConflict: ConflictResponse = {
  current_version: 5,
  submitted_version: 3,
  current_data: { policies: { enforce_tls: true } },
  message: "Version conflict: you submitted version 3 but the current version is 5.",
};

function renderDialog(
  props: Partial<React.ComponentProps<typeof ConflictDialog>> = {},
) {
  const defaultProps = {
    open: true,
    conflict: defaultConflict,
    onOverwrite: vi.fn(),
    onMerge: vi.fn(),
    onCancel: vi.fn(),
    ...props,
  };
  return {
    ...render(
      <FluentProvider theme={teamsLightTheme}>
        <ConflictDialog {...defaultProps} />
      </FluentProvider>,
    ),
    ...defaultProps,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ConflictDialog", () => {
  it("renders dialog title", async () => {
    renderDialog();
    await waitFor(() => {
      expect(screen.getByText("Version Conflict")).toBeInTheDocument();
    });
  });

  it("shows submitted version badge", async () => {
    renderDialog();
    await waitFor(() => {
      expect(screen.getByText("v3")).toBeInTheDocument();
    });
  });

  it("shows current version badge", async () => {
    renderDialog();
    await waitFor(() => {
      expect(screen.getByText("v5")).toBeInTheDocument();
    });
  });

  it("displays the conflict message", async () => {
    renderDialog();
    await waitFor(() => {
      expect(
        screen.getByText(/you submitted version 3/),
      ).toBeInTheDocument();
    });
  });

  it("calls onOverwrite when overwrite button clicked", async () => {
    const user = userEvent.setup();
    const { onOverwrite } = renderDialog();
    await waitFor(() => {
      expect(screen.getByTestId("conflict-overwrite")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("conflict-overwrite"));
    expect(onOverwrite).toHaveBeenCalledOnce();
  });

  it("calls onMerge when merge button clicked", async () => {
    const user = userEvent.setup();
    const { onMerge } = renderDialog();
    await waitFor(() => {
      expect(screen.getByTestId("conflict-merge")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("conflict-merge"));
    expect(onMerge).toHaveBeenCalledOnce();
  });

  it("calls onCancel when cancel button clicked", async () => {
    const user = userEvent.setup();
    const { onCancel } = renderDialog();
    await waitFor(() => {
      expect(screen.getByTestId("conflict-cancel")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("conflict-cancel"));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("returns null when conflict is null", () => {
    const { container } = renderDialog({ conflict: null });
    expect(
      container.querySelector("[aria-label='Conflict dialog']"),
    ).toBeNull();
  });

  it("shows resolution options text", async () => {
    renderDialog();
    await waitFor(() => {
      expect(
        screen.getByText(/choose how to resolve/i),
      ).toBeInTheDocument();
    });
  });

  it("has Overwrite option description", async () => {
    renderDialog();
    await waitFor(() => {
      const buttons = screen.getAllByText("Overwrite");
      expect(buttons.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("has Merge option description", async () => {
    renderDialog();
    await waitFor(() => {
      const buttons = screen.getAllByText("Merge");
      expect(buttons.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows warning message bar", async () => {
    renderDialog();
    await waitFor(() => {
      expect(
        screen.getByText(/modified by another user/),
      ).toBeInTheDocument();
    });
  });

  it("has accessible dialog label", async () => {
    renderDialog();
    await waitFor(() => {
      expect(
        screen.getByLabelText("Conflict dialog"),
      ).toBeInTheDocument();
    });
  });

  it("shows version labels", async () => {
    renderDialog();
    await waitFor(() => {
      expect(screen.getByText("Your version")).toBeInTheDocument();
      expect(screen.getByText("Current version")).toBeInTheDocument();
    });
  });
});
