import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import AvdAcceleratorPanel from "./AvdAcceleratorPanel";
import type {
  AvdQuestionResponse,
  AvdSkuResponse,
  AvdReferenceArchResponse,
} from "../../services/api";

const sampleQuestions: AvdQuestionResponse[] = [
  {
    id: "avd_user_count",
    category: "capacity",
    text: "How many concurrent users will use AVD?",
    type: "single_choice",
    options: [
      { value: "10-50", label: "10–50 users" },
      { value: "50-200", label: "50–200 users" },
    ],
    required: true,
    order: 1,
  },
  {
    id: "avd_user_type",
    category: "workload",
    text: "What type of users will be using AVD?",
    type: "single_choice",
    options: [
      { value: "task_worker", label: "Task worker" },
      { value: "knowledge_worker", label: "Knowledge worker" },
    ],
    required: true,
    order: 2,
  },
];

const sampleSkus: AvdSkuResponse[] = [
  {
    name: "Standard_D4s_v5",
    series: "Dsv5",
    family: "general_purpose",
    vcpus: 4,
    memory_gb: 16,
    gpu: false,
    users_per_vm: { task_worker: 6, knowledge_worker: 4 },
    recommended_users: 4,
    description: "General-purpose, 4 vCPUs.",
  },
  {
    name: "Standard_NV6ads_A10_v5",
    series: "NVadsA10v5",
    family: "gpu",
    vcpus: 6,
    memory_gb: 55,
    gpu: true,
    users_per_vm: { developer: 2 },
    recommended_users: 2,
    description: "GPU-accelerated, 6 vCPUs.",
  },
];

const sampleRefArchs: AvdReferenceArchResponse[] = [
  {
    id: "small_team",
    name: "Small Team",
    description: "Pooled desktops for up to 50 users.",
    user_count: "10-50",
    host_pool_type: "pooled",
    session_host_count: 3,
    vm_sku: "Standard_D4s_v5",
    fslogix_storage: "azure_files",
    regions: 1,
    scaling: "autoscale",
    components: ["host_pool", "workspace", "azure_files"],
  },
  {
    id: "enterprise_pooled",
    name: "Enterprise Pooled",
    description: "Large-scale pooled deployment.",
    user_count: "200-1000",
    host_pool_type: "pooled",
    session_host_count: 25,
    vm_sku: "Standard_E8s_v5",
    fslogix_storage: "azure_netapp_files",
    regions: 2,
    scaling: "autoscale",
    components: ["host_pool", "workspace", "azure_netapp_files", "scaling_plan"],
  },
];

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <FluentProvider theme={teamsLightTheme}>{ui}</FluentProvider>,
  );
}

describe("AvdAcceleratorPanel", () => {
  it("renders the panel with header and reference architectures", () => {
    renderWithProviders(
      <AvdAcceleratorPanel
        questions={sampleQuestions}
        skus={sampleSkus}
        referenceArchitectures={sampleRefArchs}
      />,
    );
    expect(screen.getByText("Azure Virtual Desktop Accelerator")).toBeTruthy();
    expect(screen.getByText("Small Team")).toBeTruthy();
    expect(screen.getByText("Enterprise Pooled")).toBeTruthy();
  });

  it("shows loading state when loading prop is true", () => {
    renderWithProviders(
      <AvdAcceleratorPanel
        questions={[]}
        skus={[]}
        referenceArchitectures={[]}
        loading={true}
      />,
    );
    expect(screen.getByTestId("avd-loading")).toBeTruthy();
  });

  it("shows error message when error prop is set", () => {
    renderWithProviders(
      <AvdAcceleratorPanel
        questions={[]}
        skus={[]}
        referenceArchitectures={[]}
        error="Something went wrong"
      />,
    );
    expect(screen.getByTestId("avd-error")).toBeTruthy();
    expect(screen.getByText("Something went wrong")).toBeTruthy();
  });

  it("calls onReferenceSelect when a reference card is clicked", async () => {
    const user = userEvent.setup();
    const onReferenceSelect = vi.fn();
    renderWithProviders(
      <AvdAcceleratorPanel
        questions={sampleQuestions}
        skus={sampleSkus}
        referenceArchitectures={sampleRefArchs}
        onReferenceSelect={onReferenceSelect}
      />,
    );
    await user.click(screen.getByTestId("avd-ref-small_team"));
    expect(onReferenceSelect).toHaveBeenCalledWith("small_team");
  });

  it("displays components when a reference architecture is selected", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <AvdAcceleratorPanel
        questions={sampleQuestions}
        skus={sampleSkus}
        referenceArchitectures={sampleRefArchs}
      />,
    );
    await user.click(screen.getByTestId("avd-ref-small_team"));
    expect(screen.getByText("host_pool")).toBeTruthy();
    expect(screen.getByText("workspace")).toBeTruthy();
    expect(screen.getByText("azure_files")).toBeTruthy();
  });

  it("disables generate button when no answers and no ref selected", () => {
    renderWithProviders(
      <AvdAcceleratorPanel
        questions={sampleQuestions}
        skus={sampleSkus}
        referenceArchitectures={sampleRefArchs}
      />,
    );
    const btn = screen.getByTestId("avd-generate-button");
    expect(btn).toHaveProperty("disabled", true);
  });

  it("enables generate button after selecting a reference architecture", async () => {
    const user = userEvent.setup();
    const onGenerate = vi.fn();
    renderWithProviders(
      <AvdAcceleratorPanel
        questions={sampleQuestions}
        skus={sampleSkus}
        referenceArchitectures={sampleRefArchs}
        onGenerate={onGenerate}
      />,
    );
    await user.click(screen.getByTestId("avd-ref-enterprise_pooled"));
    const btn = screen.getByTestId("avd-generate-button");
    expect(btn).toHaveProperty("disabled", false);
    await user.click(btn);
    expect(onGenerate).toHaveBeenCalled();
  });

  it("renders question dropdowns for each question", () => {
    renderWithProviders(
      <AvdAcceleratorPanel
        questions={sampleQuestions}
        skus={sampleSkus}
        referenceArchitectures={sampleRefArchs}
      />,
    );
    expect(
      screen.getByText("How many concurrent users will use AVD?"),
    ).toBeTruthy();
    expect(
      screen.getByText("What type of users will be using AVD?"),
    ).toBeTruthy();
  });

  it("shows host pool type badges on reference cards", () => {
    renderWithProviders(
      <AvdAcceleratorPanel
        questions={sampleQuestions}
        skus={sampleSkus}
        referenceArchitectures={sampleRefArchs}
      />,
    );
    const badges = screen.getAllByText("pooled");
    expect(badges.length).toBeGreaterThanOrEqual(2);
  });
});
