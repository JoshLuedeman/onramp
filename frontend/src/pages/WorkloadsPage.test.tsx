import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";
import { vi, describe, it, expect, beforeEach } from "vitest";

import WorkloadsPage from "./WorkloadsPage";

vi.mock("../services/api", () => ({
  api: {
    workloads: {
      list: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      importFile: vi.fn(),
    },
  },
}));

import { api } from "../services/api";

const mockedApi = api as unknown as {
  workloads: {
    list: ReturnType<typeof vi.fn>;
    create: ReturnType<typeof vi.fn>;
    update: ReturnType<typeof vi.fn>;
    delete: ReturnType<typeof vi.fn>;
    importFile: ReturnType<typeof vi.fn>;
  };
};

function renderPage() {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>
        <WorkloadsPage projectId="test-project-id" />
      </MemoryRouter>
    </FluentProvider>,
  );
}

const mockWorkload = {
  id: "wl-001",
  project_id: "test-project-id",
  name: "Web Server 01",
  type: "vm",
  source_platform: "vmware",
  cpu_cores: 4,
  memory_gb: 16.0,
  storage_gb: 500.0,
  os_type: "Windows",
  os_version: "Server 2022",
  criticality: "standard",
  compliance_requirements: [],
  dependencies: [],
  migration_strategy: "rehost",
  notes: null,
  created_at: "2024-01-01T00:00:00",
  updated_at: "2024-01-01T00:00:00",
};

beforeEach(() => {
  vi.resetAllMocks();
});

describe("WorkloadsPage rendering", () => {
  it("renders the heading", () => {
    renderPage();
    expect(screen.getByText("Workload Inventory")).toBeInTheDocument();
  });

  it("renders Import and Inventory tabs", () => {
    renderPage();
    expect(screen.getByRole("tab", { name: /Import/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Inventory/i })).toBeInTheDocument();
  });

  it("shows the drop zone by default on Import tab", () => {
    renderPage();
    expect(screen.getByText(/Drop a CSV or JSON file here/i)).toBeInTheDocument();
  });
});

describe("Import tab", () => {
  it("shows file name and Import button after selecting a file", async () => {
    renderPage();
    const input = screen.getByLabelText(/File input for workload import/i);
    const file = new File(["name,type\nweb01,vm\n"], "workloads.csv", { type: "text/csv" });
    await userEvent.upload(input, file);
    expect(screen.getAllByText(/workloads.csv/).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /^Import$/i })).toBeInTheDocument();
  });

  it("calls importFile and shows results on success", async () => {
    mockedApi.workloads.list.mockResolvedValue({ workloads: [], total: 0 });
    mockedApi.workloads.importFile.mockResolvedValue({
      imported_count: 2,
      failed_count: 0,
      errors: [],
      workloads: [
        { ...mockWorkload, id: "wl-001", name: "Web Server 01" },
        { ...mockWorkload, id: "wl-002", name: "DB Server 01" },
      ],
    });
    renderPage();
    const input = screen.getByLabelText(/File input for workload import/i);
    const file = new File(["name,type\nweb01,vm\n"], "workloads.csv", { type: "text/csv" });
    await userEvent.upload(input, file);
    const importBtn = screen.getByRole("button", { name: /^Import$/i });
    await userEvent.click(importBtn);
    await waitFor(() => {
      expect(screen.getByText(/Imported/i)).toBeInTheDocument();
    });
    expect(mockedApi.workloads.importFile).toHaveBeenCalledWith(file, "test-project-id");
  });

  it("shows row errors from import result", async () => {
    mockedApi.workloads.list.mockResolvedValue({ workloads: [], total: 0 });
    mockedApi.workloads.importFile.mockResolvedValue({
      imported_count: 1,
      failed_count: 1,
      errors: ["Row 3: Missing required field: name"],
      workloads: [mockWorkload],
    });
    renderPage();
    const input = screen.getByLabelText(/File input for workload import/i);
    await userEvent.upload(input, new File(["name\nweb01\n"], "f.csv"));
    await userEvent.click(screen.getByRole("button", { name: /^Import$/i }));
    await waitFor(() => {
      expect(screen.getByText(/Row 3: Missing required field: name/)).toBeInTheDocument();
    });
  });

  it("shows error message when import throws", async () => {
    mockedApi.workloads.importFile.mockRejectedValue(new Error("Network error"));
    renderPage();
    const input = screen.getByLabelText(/File input for workload import/i);
    await userEvent.upload(input, new File(["name\nweb01\n"], "f.csv"));
    await userEvent.click(screen.getByRole("button", { name: /^Import$/i }));
    await waitFor(() => {
      expect(screen.getByText(/Network error/)).toBeInTheDocument();
    });
  });

  it("clears file selection when Clear button is clicked", async () => {
    renderPage();
    const input = screen.getByLabelText(/File input for workload import/i);
    await userEvent.upload(input, new File(["name\nweb01\n"], "test.csv"));
    expect(screen.getAllByText(/test.csv/).length).toBeGreaterThan(0);
    await userEvent.click(screen.getByRole("button", { name: /Clear/i }));
    expect(screen.getByText(/Drop a CSV or JSON file here/i)).toBeInTheDocument();
  });
});

describe("Inventory tab", () => {
  it("loads and displays workloads when Inventory tab is selected", async () => {
    mockedApi.workloads.list.mockResolvedValue({ workloads: [mockWorkload], total: 1 });
    renderPage();
    await userEvent.click(screen.getByRole("tab", { name: /Inventory/i }));
    await waitFor(() => {
      expect(screen.getByText("Web Server 01")).toBeInTheDocument();
    });
    expect(mockedApi.workloads.list).toHaveBeenCalledWith("test-project-id");
  });

  it("shows empty state when no workloads exist", async () => {
    mockedApi.workloads.list.mockResolvedValue({ workloads: [], total: 0 });
    renderPage();
    await userEvent.click(screen.getByRole("tab", { name: /Inventory/i }));
    await waitFor(() => {
      expect(screen.getByText(/No workloads yet/i)).toBeInTheDocument();
    });
  });

  it("shows error message when list fails", async () => {
    mockedApi.workloads.list.mockRejectedValue(new Error("Server error"));
    renderPage();
    await userEvent.click(screen.getByRole("tab", { name: /Inventory/i }));
    await waitFor(() => {
      expect(screen.getByText(/Server error/)).toBeInTheDocument();
    });
  });

  it("refreshes list when Refresh button is clicked", async () => {
    mockedApi.workloads.list.mockResolvedValue({ workloads: [mockWorkload], total: 1 });
    renderPage();
    await userEvent.click(screen.getByRole("tab", { name: /Inventory/i }));
    await waitFor(() => screen.getByText("Web Server 01"));
    await userEvent.click(screen.getByRole("button", { name: /Refresh/i }));
    await waitFor(() => {
      expect(mockedApi.workloads.list).toHaveBeenCalledTimes(2);
    });
  });
});

describe("Create workload dialog", () => {
  beforeEach(async () => {
    mockedApi.workloads.list.mockResolvedValue({ workloads: [], total: 0 });
  });

  it("opens Add Workload dialog on Inventory tab", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("tab", { name: /Inventory/i }));
    await waitFor(() => screen.getByRole("button", { name: /Add Workload/i }));
    await userEvent.click(screen.getByRole("button", { name: /Add Workload/i }));
    // findByPlaceholderText confirms the dialog form is open and the name input is rendered
    expect(await screen.findByPlaceholderText(/e.g. web-server-01/i)).toBeInTheDocument();
  });

  it("creates a workload and closes dialog on success", async () => {
    mockedApi.workloads.create.mockResolvedValue({ ...mockWorkload, name: "New VM" });
    renderPage();
    await userEvent.click(screen.getByRole("tab", { name: /Inventory/i }));
    await waitFor(() => screen.getByRole("button", { name: /Add Workload/i }));
    await userEvent.click(screen.getByRole("button", { name: /Add Workload/i }));
    const nameInput = await screen.findByPlaceholderText(/e.g. web-server-01/i);
    await userEvent.type(nameInput, "New VM");
    await userEvent.click(await screen.findByRole("button", { name: /Create Workload/i }));
    await waitFor(() => {
      expect(mockedApi.workloads.create).toHaveBeenCalledWith(
        expect.objectContaining({ name: "New VM" }),
      );
    });
  });

  it("shows validation error when name is empty", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("tab", { name: /Inventory/i }));
    await waitFor(() => screen.getByRole("button", { name: /Add Workload/i }));
    // Use fireEvent to avoid pointer event sequences that may close the dialog
    fireEvent.click(screen.getByRole("button", { name: /Add Workload/i }));
    // Wait for the entire dialog to render (form + action buttons)
    await waitFor(() => {
      screen.getByPlaceholderText(/e.g. web-server-01/i);
      screen.getByRole("button", { name: /Create Workload/i });
    });
    // Focus inside the dialog first to prevent pointer events from dismissing it
    await userEvent.click(screen.getByPlaceholderText(/e.g. web-server-01/i));
    await userEvent.click(screen.getByRole("button", { name: /Create Workload/i }));
    await waitFor(() => {
      expect(screen.getByText("Name is required")).toBeInTheDocument();
    });
  });
});

describe("Delete workload", () => {
  it("deletes workload and removes from list", async () => {
    mockedApi.workloads.list.mockResolvedValue({ workloads: [mockWorkload], total: 1 });
    mockedApi.workloads.delete.mockResolvedValue({ deleted: true, id: "wl-001" });
    renderPage();
    await userEvent.click(screen.getByRole("tab", { name: /Inventory/i }));
    await waitFor(() => screen.getByText("Web Server 01"));
    await userEvent.click(screen.getByLabelText("Delete Web Server 01"));
    await waitFor(() => {
      expect(screen.getByText(/Are you sure you want to delete/i)).toBeInTheDocument();
    });
    // Use waitFor to ensure the confirmation Delete button is fully rendered before clicking
    const deleteBtn = await screen.findByRole("button", { name: /^Delete$/i });
    await waitFor(async () => {
      await userEvent.click(deleteBtn);
      expect(mockedApi.workloads.delete).toHaveBeenCalledWith("wl-001");
    });
  });
});

describe("Edit workload dialog", () => {
  it("opens edit dialog pre-filled and saves changes", async () => {
    mockedApi.workloads.list.mockResolvedValue({ workloads: [mockWorkload], total: 1 });
    mockedApi.workloads.update.mockResolvedValue({ ...mockWorkload, name: "Renamed" });
    renderPage();
    await userEvent.click(screen.getByRole("tab", { name: /Inventory/i }));
    await waitFor(() => screen.getByText("Web Server 01"));
    // Use fireEvent to avoid pointer event sequences that may close the dialog
    fireEvent.click(screen.getByLabelText("Edit Web Server 01"));
    // Wait for the entire dialog to render (form + action buttons)
    await waitFor(() => {
      screen.getByDisplayValue("Web Server 01");
      screen.getByRole("button", { name: /Save Changes/i });
    });
    const nameInput = screen.getByDisplayValue("Web Server 01");
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, "Renamed");
    await userEvent.click(screen.getByRole("button", { name: /Save Changes/i }));
    await waitFor(() => {
      expect(mockedApi.workloads.update).toHaveBeenCalledWith(
        "wl-001",
        expect.objectContaining({ name: "Renamed" }),
      );
    });
  });

  it("shows error when save fails", async () => {
    mockedApi.workloads.list.mockResolvedValue({ workloads: [mockWorkload], total: 1 });
    mockedApi.workloads.update.mockRejectedValue(new Error("Update failed"));
    renderPage();
    await userEvent.click(screen.getByRole("tab", { name: /Inventory/i }));
    await waitFor(() => screen.getByText("Web Server 01"));
    // Use fireEvent to avoid pointer event sequences that may close the dialog
    fireEvent.click(screen.getByLabelText("Edit Web Server 01"));
    // Wait for the entire dialog to render (form + action buttons)
    await waitFor(() => {
      screen.getByDisplayValue("Web Server 01");
      screen.getByRole("button", { name: /Save Changes/i });
    });
    // Focus inside the dialog first to prevent pointer events from dismissing it
    await userEvent.click(screen.getByDisplayValue("Web Server 01"));
    await userEvent.click(screen.getByRole("button", { name: /Save Changes/i }));
    await waitFor(() => {
      expect(screen.getByText("Update failed")).toBeInTheDocument();
    });
  });
});

describe("Import tab drag-and-drop", () => {
  it("accepts a dropped file", async () => {
    renderPage();
    const dropZone = screen.getByRole("button", { name: /drop zone/i });
    const file = new File(["name,type\nApp,vm"], "workloads.csv", { type: "text/csv" });
    const dt = { files: [file], types: ["Files"] };
    fireEvent.dragOver(dropZone, { dataTransfer: dt });
    fireEvent.drop(dropZone, { dataTransfer: dt });
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /^Import$/i })).toBeInTheDocument();
    });
  });
});
