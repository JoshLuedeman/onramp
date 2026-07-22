#!/usr/bin/env bash
# ============================================================================
# Shared installer for the GitHub Copilot CLI and the hve-core-all plugin
# (github.com/microsoft/hve-core).
#
# This script is used by both:
#   - .github/workflows/copilot-setup-steps.yml (Copilot cloud agent sandbox)
#   - .devcontainer/devcontainer.json (postCreateCommand, local dev containers)
#
# IMPORTANT: This install is best-effort and MUST NOT be fatal. The dev
# container / cloud sandbox must still start successfully even if any step
# here fails (e.g. missing auth, network restrictions, registry issues).
# ============================================================================
set -euo pipefail

echo "Installing GitHub Copilot CLI..."
npm install -g @github/copilot || echo "::warning::copilot CLI install failed"

echo "Adding microsoft/hve-core plugin marketplace..."
copilot plugin marketplace add microsoft/hve-core || echo "::warning::marketplace add failed"

echo "Installing hve-core-all plugin..."
copilot plugin install hve-core-all@hve-core || echo "::warning::hve-core-all install failed"

echo "Listing installed Copilot CLI plugins..."
copilot plugin list || true
