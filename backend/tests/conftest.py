"""Shared constants and fixtures for backend tests."""

import os

# Enable debug mode for all tests so mock auth is active
# (matches pre-existing behavior where tests ran with mock auth).
os.environ.setdefault("ONRAMP_DEBUG", "true")

SQLITE_TEST_URL = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"
