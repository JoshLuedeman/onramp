import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import ConfidentialComputingPanel from "./ConfidentialComputingPanel";
import type { ConfidentialOption, ConfidentialVmSku, ConfidentialRegion } from "../../services/api";

const sampleOptions: ConfidentialOption[] = [
  {
    id: "confidential_vms",
    name: "Confidential VMs",
    category: "compute",
    tee_types: ["SEV-SNP"],
    description: "Azure Confidential VMs use AMD SEV-SNP.",
    use_cases: ["Lift-and-shift migration", "Multi-tenant isolation"],
    vm_series: ["DCasv5"],
    attestation_supported: true,
  },
  {
    id: "sgx_enclaves",
    name: "SGX Enclaves",
    category: "compute",
    tee_types: ["SGX"],
    description: "Intel SGX enclaves for app-level isolation.",
    use_cases: ["Secure multi-party computation"],
    vm_series: ["DCsv3"],
    attestation_supported: true,
  },
  {
    id: "confidential_ledger",
    name: "Azure Confidential Ledger",
    category: "data",
    tee_types: ["SGX"],
    description: "Tamper-proof data store.",
    use_cases: ["Immutable audit logs"],
    vm_series: [],
    attestation_supported: true,
  },
];

const sampleSkus: ConfidentialVmSku[] = [
  {
    name: "Standard_DC2as_v5",
    series: "DCasv5",
    vcpus: 2,
    memory_gb: 8,
    tee_type: "SEV-SNP",
    vendor: "AMD",
    max_data_disks: 4,
    enclave_memory_mb: null,
    description: "Confidential VM, 2 vCPUs.",
  },
  {
    name: "Standard_DC2s_v3",
    series: "DCsv3",
    vcpus: 2,
    memory_gb: 16,
    tee_type: "SGX",
    vendor: "Intel",
    max_data_disks: 4,
    enclave_memory_mb: 8192,
    description: "SGX VM, 2 vCPUs.",
  },
];

const sampleRegions: ConfidentialRegion[] = [
  {
    name: "eastus",
    display_name: "East US",
    tee_types: ["SEV-SNP", "SGX"],
    services: ["confidential_vms", "sgx_enclaves", "confidential_ledger"],
  },
  {
    name: "westus",
    display_name: "West US",
    tee_types: ["SEV-SNP"],
    services: ["confidential_vms"],
  },
];

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <FluentProvider theme={teamsLightTheme}>{ui}</FluentProvider>,
  );
}

describe("ConfidentialComputingPanel", () => {
  it("renders the panel with header and options", () => {
    renderWithProviders(
      <ConfidentialComputingPanel
        options={sampleOptions}
        vmSkus={sampleSkus}
        regions={sampleRegions}
      />,
    );
    expect(screen.getByText("Confidential Computing")).toBeTruthy();
    expect(screen.getByText("Confidential VMs")).toBeTruthy();
    expect(screen.getByText("SGX Enclaves")).toBeTruthy();
    expect(screen.getByText("Azure Confidential Ledger")).toBeTruthy();
  });

  it("shows loading state when loading prop is true", () => {
    renderWithProviders(
      <ConfidentialComputingPanel
        options={[]}
        vmSkus={[]}
        regions={[]}
        loading={true}
      />,
    );
    expect(screen.getByTestId("cc-loading")).toBeTruthy();
  });

  it("shows error message when error prop is set", () => {
    renderWithProviders(
      <ConfidentialComputingPanel
        options={[]}
        vmSkus={[]}
        regions={[]}
        error="Failed to load"
      />,
    );
    expect(screen.getByTestId("cc-error")).toBeTruthy();
    expect(screen.getByText("Failed to load")).toBeTruthy();
  });

  it("calls onOptionSelect when a CC option is clicked", async () => {
    const user = userEvent.setup();
    const onOptionSelect = vi.fn();
    renderWithProviders(
      <ConfidentialComputingPanel
        options={sampleOptions}
        vmSkus={sampleSkus}
        regions={sampleRegions}
        onOptionSelect={onOptionSelect}
      />,
    );
    await user.click(screen.getByTestId("cc-option-confidential_vms"));
    expect(onOptionSelect).toHaveBeenCalledWith("confidential_vms");
  });

  it("disables apply button when no option is selected", () => {
    renderWithProviders(
      <ConfidentialComputingPanel
        options={sampleOptions}
        vmSkus={sampleSkus}
        regions={sampleRegions}
      />,
    );
    const applyBtn = screen.getByTestId("cc-apply-button");
    expect(applyBtn).toHaveProperty("disabled", true);
  });

  it("calls onApply with config when apply button is clicked", async () => {
    const user = userEvent.setup();
    const onApply = vi.fn();
    renderWithProviders(
      <ConfidentialComputingPanel
        options={sampleOptions}
        vmSkus={sampleSkus}
        regions={sampleRegions}
        onApply={onApply}
      />,
    );
    // Select an option first to enable apply
    await user.click(screen.getByTestId("cc-option-confidential_vms"));
    await user.click(screen.getByTestId("cc-apply-button"));
    expect(onApply).toHaveBeenCalledWith(
      expect.objectContaining({
        selectedOption: "confidential_vms",
        attestationEnabled: true,
      }),
    );
  });

  it("displays use cases when an option is selected", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <ConfidentialComputingPanel
        options={sampleOptions}
        vmSkus={sampleSkus}
        regions={sampleRegions}
      />,
    );
    await user.click(screen.getByTestId("cc-option-confidential_vms"));
    expect(screen.getByText("Lift-and-shift migration")).toBeTruthy();
    expect(screen.getByText("Multi-tenant isolation")).toBeTruthy();
  });

  it("shows TEE badge on each option card", () => {
    renderWithProviders(
      <ConfidentialComputingPanel
        options={sampleOptions}
        vmSkus={sampleSkus}
        regions={sampleRegions}
      />,
    );
    expect(screen.getByText("SEV-SNP")).toBeTruthy();
    const sgxBadges = screen.getAllByText("SGX");
    expect(sgxBadges.length).toBeGreaterThanOrEqual(1);
  });
});
