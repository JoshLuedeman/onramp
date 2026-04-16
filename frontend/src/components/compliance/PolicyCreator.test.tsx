import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";

// ── Mocks ───────────────────────────────────────────────────────────────────

const mockGenerate = vi.fn().mockResolvedValue({
  name: "deny-public-ips",
  display_name: "Deny Public IPs",
  description: "Prevent creation of public IP addresses",
  mode: "All",
  policy_rule: {
    if: { field: "type", equals: "Microsoft.Network/publicIPAddresses" },
    then: { effect: "Deny" },
  },
  parameters: {},
  metadata: { category: "Network" },
});

const mockValidate = vi.fn().mockResolvedValue({
  valid: true,
  errors: [],
  warnings: [],
});

const mockGetLibrary = vi.fn().mockResolvedValue([
  {
    id: "restrict-vm-sizes",
    name: "Restrict VM Sizes",
    description: "Only allow specific VM SKU sizes.",
    category: "Compute",
    policy_json: { name: "restrict-vm-sizes", mode: "All", policy_rule: {} },
  },
  {
    id: "require-tags",
    name: "Require Tags",
    description: "Enforce mandatory tags.",
    category: "Tags",
    policy_json: { name: "require-tags", mode: "Indexed", policy_rule: {} },
  },
]);

const mockApply = vi.fn().mockResolvedValue(undefined);

vi.mock("../../services/api", async () => {
  const actual = await vi.importActual("../../services/api");
  return {
    ...actual,
    api: {
      policies: {
        generate: (...args: unknown[]) => mockGenerate(...args),
        validate: (...args: unknown[]) => mockValidate(...args),
        getLibrary: (...args: unknown[]) => mockGetLibrary(...args),
        apply: (...args: unknown[]) => mockApply(...args),
      },
    },
  };
});

import PolicyCreator from "./PolicyCreator";

// ── Helper ──────────────────────────────────────────────────────────────────

function renderComponent() {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>
        <PolicyCreator />
      </MemoryRouter>
    </FluentProvider>,
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("PolicyCreator", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without crashing", () => {
    const { container } = renderComponent();
    expect(container).toBeTruthy();
    expect(screen.getByTestId("policy-creator")).toBeInTheDocument();
  });

  it("renders the title and tabs", () => {
    renderComponent();
    expect(screen.getByText("Policy Creator")).toBeInTheDocument();
    // Fluent UI Tabs render visible + reserved-space text, so use getAllByText
    expect(screen.getAllByText("Generate Policy").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Policy Library").length).toBeGreaterThanOrEqual(1);
  });

  it("renders description input and generate button", () => {
    renderComponent();
    expect(screen.getByTestId("policy-description-input")).toBeInTheDocument();
    expect(screen.getByTestId("generate-policy-btn")).toBeInTheDocument();
  });

  it("generate button is disabled when input is empty", () => {
    renderComponent();
    const btn = screen.getByTestId("generate-policy-btn");
    expect(btn).toBeDisabled();
  });

  it("generates a policy and shows the preview", async () => {
    const user = userEvent.setup();
    renderComponent();

    // Type a description using fireEvent for Fluent UI textarea
    const textarea = screen.getByPlaceholderText(
      /Deny creation of public IP addresses/,
    );
    fireEvent.change(textarea, {
      target: { value: "Block public IPs" },
    });

    // Click generate
    const btn = screen.getByTestId("generate-policy-btn");
    await user.click(btn);

    await waitFor(() => {
      expect(mockGenerate).toHaveBeenCalledWith("Block public IPs");
    });

    await waitFor(() => {
      expect(screen.getByTestId("policy-preview")).toBeInTheDocument();
    });

    expect(screen.getByTestId("policy-json")).toBeInTheDocument();
  });

  it("shows validation badge after generation", async () => {
    const user = userEvent.setup();
    renderComponent();

    const textarea = screen.getByPlaceholderText(
      /Deny creation of public IP addresses/,
    );
    fireEvent.change(textarea, {
      target: { value: "Block public IPs" },
    });

    await user.click(screen.getByTestId("generate-policy-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("validation-status")).toBeInTheDocument();
    });

    expect(screen.getByText("Valid")).toBeInTheDocument();
  });

  it("shows apply button after generation", async () => {
    const user = userEvent.setup();
    renderComponent();

    const textarea = screen.getByPlaceholderText(
      /Deny creation of public IP addresses/,
    );
    fireEvent.change(textarea, {
      target: { value: "Block public IPs" },
    });

    await user.click(screen.getByTestId("generate-policy-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("apply-policy-btn")).toBeInTheDocument();
    });
  });

  it("loads and displays policy library when Library tab is clicked", async () => {
    const user = userEvent.setup();
    renderComponent();

    const libraryTabs = screen.getAllByText("Policy Library");
    await user.click(libraryTabs[0]);

    await waitFor(() => {
      expect(mockGetLibrary).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByTestId("policy-library")).toBeInTheDocument();
    });

    expect(screen.getByText("Restrict VM Sizes")).toBeInTheDocument();
    expect(screen.getByText("Require Tags")).toBeInTheDocument();
  });

  it("shows error message when generation fails", async () => {
    mockGenerate.mockRejectedValueOnce(new Error("API failure"));
    const user = userEvent.setup();
    renderComponent();

    const textarea = screen.getByPlaceholderText(
      /Deny creation of public IP addresses/,
    );
    fireEvent.change(textarea, {
      target: { value: "Block public IPs" },
    });

    await user.click(screen.getByTestId("generate-policy-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("policy-error")).toBeInTheDocument();
    });

    expect(screen.getByText("API failure")).toBeInTheDocument();
  });

  it("shows invalid badge when validation fails", async () => {
    mockValidate.mockResolvedValueOnce({
      valid: false,
      errors: ["Missing policy_rule"],
      warnings: [],
    });
    const user = userEvent.setup();
    renderComponent();

    const textarea = screen.getByPlaceholderText(
      /Deny creation of public IP addresses/,
    );
    fireEvent.change(textarea, {
      target: { value: "Block public IPs" },
    });

    await user.click(screen.getByTestId("generate-policy-btn"));

    await waitFor(() => {
      expect(screen.getByText("Invalid")).toBeInTheDocument();
    });
  });
});
