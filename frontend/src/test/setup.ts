import "@testing-library/jest-dom/vitest";
import { configure } from "@testing-library/react";

// Polyfill ResizeObserver for jsdom (used by Fluent UI MessageBar)
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Increase async utility timeout to handle coverage instrumentation overhead
// (Fluent UI Dialog portals can be slow to mount under V8 coverage)
configure({ asyncUtilTimeout: 5000 });
