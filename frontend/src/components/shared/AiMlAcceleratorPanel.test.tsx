import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import AiMlAcceleratorPanel from "./AiMlAcceleratorPanel";
import type { AiMlGpuSku, AiMlReferenceArchitecture } from "../../services/api";

const sampleGpuSkus: AiMlGpuSku[] = [
  {
    id: "nc4as_t4_v3",
    name: "Standard_NC4as_T4_v3",
    family: "NC",
    gpu_type: "T4",
    gpu_count: 1,
    gpu_memory_gb: 16,
    vcpus: 4,
    ram_gb: 28,
    use_case: "Cost-effective inference",
    price_tier: "standard",
  },
  {
    id: "nc24ads_a100_v4",
    name: "Standard_NC24ads_A100_v4",
    family: "NC",
    gpu_type: "A100",
    gpu_count: 1,
    gpu_memory_gb: 80,
    vcpus: 24,
    ram_gb: 220,
    use_case: "Large-scale training",
    price_tier: "premium",
  },
];

const sampleRefArchs: AiMlReferenceArchitecture[] = [
  {
    id: "small_team",
    name: "Small Team ML Workspace",
    description: "A cost-effective setup for 1-5 data scientists.",
    team_size: "1-5",
    use_case: "Experimentation",
    services: ["Azure ML Workspace", "Compute Instance", "Storage Account"],
    estimated_monthly_cost_usd: 500,
    gpu_type: "T4",
    mlops_level: "ad_hoc",
  },
  {
    id: "enterprise_training",
    name: "Enterprise Training Platform",
    description: "Production-grade ML platform for large teams.",
    team_size: "20-50+",
    use_case: "Large-scale training",
    services: ["Azure ML Workspace", "Compute Cluster", "ADLS Gen2", "Databricks"],
    estimated_monthly_cost_usd: 15000,
    gpu_type: "A100",
    mlops_level: "full_mlops",
  },
];

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <FluentProvider theme={teamsLightTheme}>{ui}</FluentProvider>,
  );
}

describe("AiMlAcceleratorPanel", () => {
  it("renders the panel with header and reference architectures", () => {
    renderWithProviders(
      <AiMlAcceleratorPanel
        gpuSkus={sampleGpuSkus}
        referenceArchitectures={sampleRefArchs}
      />,
    );
    expect(screen.getByText("AI/ML Landing Zone Accelerator")).toBeTruthy();
    expect(screen.getByText("Small Team ML Workspace")).toBeTruthy();
    expect(screen.getByText("Enterprise Training Platform")).toBeTruthy();
  });

  it("shows loading state when loading prop is true", () => {
    renderWithProviders(
      <AiMlAcceleratorPanel
        gpuSkus={[]}
        referenceArchitectures={[]}
        loading={true}
      />,
    );
    expect(screen.getByTestId("aiml-loading")).toBeTruthy();
  });

  it("shows error message when error prop is set", () => {
    renderWithProviders(
      <AiMlAcceleratorPanel
        gpuSkus={[]}
        referenceArchitectures={[]}
        error="Failed to load AI/ML data"
      />,
    );
    expect(screen.getByTestId("aiml-error")).toBeTruthy();
    expect(screen.getByText("Failed to load AI/ML data")).toBeTruthy();
  });

  it("calls onReferenceArchSelect when a ref arch card is clicked", async () => {
    const user = userEvent.setup();
    const onReferenceArchSelect = vi.fn();
    renderWithProviders(
      <AiMlAcceleratorPanel
        gpuSkus={sampleGpuSkus}
        referenceArchitectures={sampleRefArchs}
        onReferenceArchSelect={onReferenceArchSelect}
      />,
    );
    await user.click(screen.getByTestId("aiml-ref-arch-small_team"));
    expect(onReferenceArchSelect).toHaveBeenCalledWith("small_team");
  });

  it("disables apply button when no GPU or ref arch is selected", () => {
    renderWithProviders(
      <AiMlAcceleratorPanel
        gpuSkus={sampleGpuSkus}
        referenceArchitectures={sampleRefArchs}
      />,
    );
    const applyBtn = screen.getByTestId("aiml-apply-button");
    expect(applyBtn).toHaveProperty("disabled", true);
  });

  it("enables apply and calls onApply when ref arch is selected", async () => {
    const user = userEvent.setup();
    const onApply = vi.fn();
    renderWithProviders(
      <AiMlAcceleratorPanel
        gpuSkus={sampleGpuSkus}
        referenceArchitectures={sampleRefArchs}
        onApply={onApply}
      />,
    );
    await user.click(screen.getByTestId("aiml-ref-arch-enterprise_training"));
    await user.click(screen.getByTestId("aiml-apply-button"));
    expect(onApply).toHaveBeenCalledWith(
      expect.objectContaining({
        selectedReferenceArch: "enterprise_training",
      }),
    );
  });

  it("displays services list when a ref arch is selected", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <AiMlAcceleratorPanel
        gpuSkus={sampleGpuSkus}
        referenceArchitectures={sampleRefArchs}
      />,
    );
    await user.click(screen.getByTestId("aiml-ref-arch-small_team"));
    expect(screen.getByText("Azure ML Workspace")).toBeTruthy();
    expect(screen.getByText("Compute Instance")).toBeTruthy();
    expect(screen.getByText("Storage Account")).toBeTruthy();
  });

  it("shows GPU type badge on reference architecture cards", () => {
    renderWithProviders(
      <AiMlAcceleratorPanel
        gpuSkus={sampleGpuSkus}
        referenceArchitectures={sampleRefArchs}
      />,
    );
    expect(screen.getByText("T4")).toBeTruthy();
    const a100Badges = screen.getAllByText("A100");
    expect(a100Badges.length).toBeGreaterThanOrEqual(1);
  });
});
