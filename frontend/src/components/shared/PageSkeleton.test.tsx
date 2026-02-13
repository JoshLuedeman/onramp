import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import PageSkeleton from "./PageSkeleton";

describe("PageSkeleton", () => {
  it("renders without crashing", () => {
    const { container } = render(
      <FluentProvider theme={teamsLightTheme}><PageSkeleton /></FluentProvider>
    );
    expect(container.firstChild).toBeTruthy();
  });

  it("renders multiple skeleton items", () => {
    const { container } = render(
      <FluentProvider theme={teamsLightTheme}><PageSkeleton /></FluentProvider>
    );
    // Skeleton renders divs with animation
    const skeletons = container.querySelectorAll("[class]");
    expect(skeletons.length).toBeGreaterThan(0);
  });
});
