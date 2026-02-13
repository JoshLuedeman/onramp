import { describe, it, expect } from "vitest";
// The module re-exports type-only interfaces from services/api.
// We verify the module can be imported without errors.
import * as types from "./index";

describe("types/index", () => {
  it("module exports exist", () => {
    expect(types).toBeDefined();
  });
});
