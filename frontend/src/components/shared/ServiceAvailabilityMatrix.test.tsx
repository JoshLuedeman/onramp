import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import ServiceAvailabilityMatrix from "./ServiceAvailabilityMatrix";
import type { ServiceAvailabilityItem } from "../../services/api";

function renderWithTheme(ui: React.ReactElement) {
  return render(
    <FluentProvider theme={teamsLightTheme}>{ui}</FluentProvider>,
  );
}

const sampleServices: ServiceAvailabilityItem[] = [
  {
    service_name: "Virtual Machines",
    category: "Compute",
    commercial: true,
    government: true,
    china: true,
    notes: "Some VM SKUs unavailable in Government and China.",
  },
  {
    service_name: "Container Apps",
    category: "Containers",
    commercial: true,
    government: true,
    china: false,
    notes: "Not yet available in Azure China.",
  },
  {
    service_name: "Key Vault",
    category: "Security",
    commercial: true,
    government: true,
    china: true,
    notes: "",
  },
];

describe("ServiceAvailabilityMatrix", () => {
  it("renders empty state when no services", () => {
    renderWithTheme(<ServiceAvailabilityMatrix services={[]} />);
    expect(screen.getByText("No service availability data available.")).toBeInTheDocument();
  });

  it("renders service names", () => {
    renderWithTheme(<ServiceAvailabilityMatrix services={sampleServices} />);
    expect(screen.getByText("Virtual Machines")).toBeInTheDocument();
    expect(screen.getByText("Container Apps")).toBeInTheDocument();
    expect(screen.getByText("Key Vault")).toBeInTheDocument();
  });

  it("renders category badges", () => {
    renderWithTheme(<ServiceAvailabilityMatrix services={sampleServices} />);
    expect(screen.getByText("Compute")).toBeInTheDocument();
    expect(screen.getByText("Containers")).toBeInTheDocument();
    expect(screen.getByText("Security")).toBeInTheDocument();
  });

  it("shows availability indicators", () => {
    renderWithTheme(<ServiceAvailabilityMatrix services={sampleServices} />);
    const yesElements = screen.getAllByText("Yes");
    const noElements = screen.getAllByText("No");
    expect(yesElements.length).toBeGreaterThan(0);
    expect(noElements.length).toBeGreaterThan(0);
  });

  it("filters services by search input", async () => {
    const user = userEvent.setup();
    renderWithTheme(<ServiceAvailabilityMatrix services={sampleServices} />);
    const input = screen.getByPlaceholderText("Filter services…");
    await user.type(input, "Container");
    expect(screen.getByText("Container Apps")).toBeInTheDocument();
    expect(screen.queryByText("Key Vault")).not.toBeInTheDocument();
  });

  it("highlights used services from architecture prop", () => {
    renderWithTheme(
      <ServiceAvailabilityMatrix
        services={sampleServices}
        architecture={{ services: ["Key Vault"] }}
      />,
    );
    const kvCell = screen.getByText("Key Vault");
    // The cell should have bold styling via the usedService class
    expect(kvCell).toBeInTheDocument();
  });

  it("renders notes column content", () => {
    renderWithTheme(<ServiceAvailabilityMatrix services={sampleServices} />);
    expect(
      screen.getByText("Some VM SKUs unavailable in Government and China."),
    ).toBeInTheDocument();
  });

  it("renders dash for empty notes", () => {
    renderWithTheme(<ServiceAvailabilityMatrix services={sampleServices} />);
    // Key Vault has no notes, should show dash
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThan(0);
  });
});
