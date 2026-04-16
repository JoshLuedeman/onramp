import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import SapAcceleratorPanel from "./SapAcceleratorPanel";
import type { SapQuestion, SapCertifiedSku, SapBestPractice } from "../../services/api";

const sampleQuestions: SapQuestion[] = [
  {
    id: "sap_product",
    text: "Which SAP product are you deploying?",
    type: "single_choice",
    options: [
      { value: "s4hana", label: "SAP S/4HANA" },
      { value: "ecc", label: "SAP ECC" },
    ],
    required: true,
    category: "sap",
    help_text: "Select the primary SAP product.",
  },
  {
    id: "sap_database",
    text: "Which database platform will you use?",
    type: "single_choice",
    options: [
      { value: "hana", label: "SAP HANA" },
      { value: "sql_server", label: "SQL Server" },
    ],
    required: true,
    category: "sap",
    help_text: "Database engine for the SAP system.",
  },
];

const sampleSkus: SapCertifiedSku[] = [
  {
    name: "Standard_M64s",
    series: "M",
    vcpus: 64,
    memory_gb: 1024,
    saps_rating: 63140,
    max_hana_memory_gb: 1024,
    tier: "hana",
    description: "Large HANA workloads",
  },
  {
    name: "Standard_E16s_v5",
    series: "Ev5",
    vcpus: 16,
    memory_gb: 128,
    saps_rating: 17400,
    max_hana_memory_gb: 0,
    tier: "app",
    description: "Large app server",
  },
];

const sampleBestPractices: SapBestPractice[] = [
  {
    id: "hana_sizing",
    category: "sizing",
    title: "Use SAP Quick Sizer for HANA memory estimation",
    description: "Run the SAP Quick Sizer tool.",
    severity: "critical",
    link: "https://example.com",
  },
  {
    id: "certified_vms",
    category: "compute",
    title: "Use only SAP-certified VM SKUs",
    description: "Azure M-series and Mv2-series VMs are certified.",
    severity: "critical",
    link: "https://example.com",
  },
];

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <FluentProvider theme={teamsLightTheme}>{ui}</FluentProvider>,
  );
}

describe("SapAcceleratorPanel", () => {
  it("renders the panel with header and controls", () => {
    renderWithProviders(
      <SapAcceleratorPanel
        questions={sampleQuestions}
        skus={sampleSkus}
        bestPractices={sampleBestPractices}
      />,
    );
    expect(screen.getByText("SAP on Azure Accelerator")).toBeTruthy();
    expect(screen.getByTestId("sap-product-dropdown")).toBeTruthy();
    expect(screen.getByTestId("sap-database-dropdown")).toBeTruthy();
  });

  it("shows loading state when loading prop is true", () => {
    renderWithProviders(
      <SapAcceleratorPanel
        questions={[]}
        skus={[]}
        bestPractices={[]}
        loading={true}
      />,
    );
    expect(screen.getByTestId("sap-loading")).toBeTruthy();
  });

  it("shows error message when error prop is set", () => {
    renderWithProviders(
      <SapAcceleratorPanel
        questions={[]}
        skus={[]}
        bestPractices={[]}
        error="Failed to load SAP data"
      />,
    );
    expect(screen.getByTestId("sap-error")).toBeTruthy();
    expect(screen.getByText("Failed to load SAP data")).toBeTruthy();
  });

  it("displays HANA-certified SKU cards", () => {
    renderWithProviders(
      <SapAcceleratorPanel
        questions={sampleQuestions}
        skus={sampleSkus}
        bestPractices={sampleBestPractices}
      />,
    );
    expect(screen.getByText("Standard_M64s")).toBeTruthy();
    expect(screen.getByText("Large HANA workloads")).toBeTruthy();
  });

  it("displays best practices", () => {
    renderWithProviders(
      <SapAcceleratorPanel
        questions={sampleQuestions}
        skus={sampleSkus}
        bestPractices={sampleBestPractices}
      />,
    );
    expect(
      screen.getByText("Use SAP Quick Sizer for HANA memory estimation"),
    ).toBeTruthy();
    expect(
      screen.getByText("Use only SAP-certified VM SKUs"),
    ).toBeTruthy();
  });

  it("disables generate button when no product/database selected", () => {
    renderWithProviders(
      <SapAcceleratorPanel
        questions={sampleQuestions}
        skus={sampleSkus}
        bestPractices={sampleBestPractices}
      />,
    );
    const btn = screen.getByTestId("sap-generate-button");
    expect(btn).toHaveProperty("disabled", true);
  });

  it("displays questionnaire section when questions are provided", () => {
    renderWithProviders(
      <SapAcceleratorPanel
        questions={sampleQuestions}
        skus={sampleSkus}
        bestPractices={sampleBestPractices}
      />,
    );
    expect(
      screen.getByText("Questionnaire (2 questions)"),
    ).toBeTruthy();
  });

  it("calls onApply when apply button is clicked after selection", async () => {
    const user = userEvent.setup();
    const onApply = vi.fn();
    renderWithProviders(
      <SapAcceleratorPanel
        questions={sampleQuestions}
        skus={sampleSkus}
        bestPractices={sampleBestPractices}
        onApply={onApply}
      />,
    );

    // Select product via dropdown
    const productDropdown = screen.getByTestId("sap-product-dropdown");
    await user.click(productDropdown);
    const s4hanaOption = await screen.findByText("SAP S/4HANA");
    await user.click(s4hanaOption);

    // Click apply
    const applyBtn = screen.getByTestId("sap-apply-button");
    await user.click(applyBtn);
    expect(onApply).toHaveBeenCalledWith(
      expect.objectContaining({
        selectedProduct: "s4hana",
      }),
    );
  });
});
