import "@testing-library/jest-dom/vitest";

// Polyfill ResizeObserver for jsdom (used by Fluent UI MessageBar)
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};
