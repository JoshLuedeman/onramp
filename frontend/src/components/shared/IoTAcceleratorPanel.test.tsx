import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import IoTAcceleratorPanel from "./IoTAcceleratorPanel";
import type { IoTQuestion, IoTBestPractice } from "../../services/api";

const sampleQuestions: IoTQuestion[] = [
  {
    id: "device_count",
    text: "How many devices will connect to the platform?",
    type: "single_choice",
    options: ["100", "1K", "10K", "100K", "1M+"],
    default: "1K",
    category: "scale",
    help_text: "Device count determines IoT Hub tier.",
  },
  {
    id: "device_type",
    text: "What type of devices will you connect?",
    type: "single_choice",
    options: ["sensors", "gateways", "industrial", "consumer", "vehicles"],
    default: "sensors",
    category: "device",
    help_text: "Device type influences protocol selection.",
  },
  {
    id: "protocol",
    text: "Which communication protocol will devices use?",
    type: "single_choice",
    options: ["MQTT", "AMQP", "HTTPS", "Modbus", "OPC-UA"],
    default: "MQTT",
    category: "connectivity",
    help_text: "MQTT is recommended for constrained devices.",
  },
];

const sampleBestPractices: IoTBestPractice[] = [
  {
    id: "bp_use_dps",
    category: "provisioning",
    title: "Use Device Provisioning Service",
    description: "DPS automates device registration.",
    priority: "high",
  },
  {
    id: "bp_edge_filtering",
    category: "edge",
    title: "Filter data at the edge",
    description: "Reduce cloud ingestion costs.",
    priority: "high",
  },
];

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <FluentProvider theme={teamsLightTheme}>{ui}</FluentProvider>,
  );
}

describe("IoTAcceleratorPanel", () => {
  it("renders the panel with header and questions", () => {
    renderWithProviders(
      <IoTAcceleratorPanel
        questions={sampleQuestions}
        bestPractices={sampleBestPractices}
      />,
    );
    expect(screen.getByText("IoT Landing Zone Accelerator")).toBeTruthy();
    expect(
      screen.getByText("How many devices will connect to the platform?"),
    ).toBeTruthy();
    expect(
      screen.getByText("What type of devices will you connect?"),
    ).toBeTruthy();
  });

  it("shows loading state when loading prop is true", () => {
    renderWithProviders(
      <IoTAcceleratorPanel
        questions={[]}
        bestPractices={[]}
        loading={true}
      />,
    );
    expect(screen.getByTestId("iot-loading")).toBeTruthy();
  });

  it("shows error message when error prop is set", () => {
    renderWithProviders(
      <IoTAcceleratorPanel
        questions={[]}
        bestPractices={[]}
        error="Failed to load IoT data"
      />,
    );
    expect(screen.getByTestId("iot-error")).toBeTruthy();
    expect(screen.getByText("Failed to load IoT data")).toBeTruthy();
  });

  it("disables generate button when no answers are selected", () => {
    renderWithProviders(
      <IoTAcceleratorPanel
        questions={sampleQuestions}
        bestPractices={sampleBestPractices}
      />,
    );
    const generateBtn = screen.getByTestId("iot-generate-button");
    expect(generateBtn).toHaveProperty("disabled", true);
  });

  it("renders best practices section", () => {
    renderWithProviders(
      <IoTAcceleratorPanel
        questions={sampleQuestions}
        bestPractices={sampleBestPractices}
      />,
    );
    expect(screen.getByText("Best Practices")).toBeTruthy();
    expect(
      screen.getByText("Use Device Provisioning Service"),
    ).toBeTruthy();
    expect(screen.getByText("Filter data at the edge")).toBeTruthy();
  });

  it("renders question cards with test IDs", () => {
    renderWithProviders(
      <IoTAcceleratorPanel
        questions={sampleQuestions}
        bestPractices={sampleBestPractices}
      />,
    );
    expect(screen.getByTestId("iot-question-device_count")).toBeTruthy();
    expect(screen.getByTestId("iot-question-device_type")).toBeTruthy();
    expect(screen.getByTestId("iot-question-protocol")).toBeTruthy();
  });
});
