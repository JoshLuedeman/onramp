"""Tests for the PromptRegistry — in-memory prompt version management."""

import pytest

from app.services.prompt_registry import PromptEntry, PromptRegistry, prompt_registry


@pytest.fixture(autouse=True)
def _reset_registry():
    """Reset the singleton between tests."""
    PromptRegistry.reset()
    yield
    PromptRegistry.reset()


class TestSingleton:
    """Test singleton pattern."""

    def test_same_instance(self):
        a = PromptRegistry()
        b = PromptRegistry()
        assert a is b

    def test_reset_clears_instance(self):
        a = PromptRegistry()
        PromptRegistry.reset()
        b = PromptRegistry()
        assert a is not b


class TestRegisterPrompt:
    """Test prompt registration."""

    def test_register_and_retrieve(self):
        reg = PromptRegistry()
        entry = reg.register_prompt("test", version=1, template="Hello {name}")
        assert isinstance(entry, PromptEntry)
        assert entry.name == "test"
        assert entry.version == 1

    def test_register_multiple_versions(self):
        reg = PromptRegistry()
        reg.register_prompt("test", version=1, template="v1")
        reg.register_prompt("test", version=2, template="v2")
        assert reg.get_prompt("test", version=1).template == "v1"
        assert reg.get_prompt("test", version=2).template == "v2"

    def test_latest_version_is_active(self):
        reg = PromptRegistry()
        reg.register_prompt("test", version=1, template="v1")
        reg.register_prompt("test", version=2, template="v2")
        v1 = reg.get_prompt("test", version=1)
        v2 = reg.get_prompt("test", version=2)
        assert v1.is_active is False
        assert v2.is_active is True

    def test_register_with_metadata(self):
        reg = PromptRegistry()
        entry = reg.register_prompt(
            "test", version=1, template="tmpl", metadata={"source": "custom"}
        )
        assert entry.metadata == {"source": "custom"}


class TestGetPrompt:
    """Test prompt retrieval."""

    def test_get_nonexistent_returns_none(self):
        reg = PromptRegistry()
        assert reg.get_prompt("nonexistent") is None

    def test_get_nonexistent_version_returns_none(self):
        reg = PromptRegistry()
        reg.register_prompt("test", version=1, template="v1")
        assert reg.get_prompt("test", version=99) is None

    def test_get_latest_without_version(self):
        reg = PromptRegistry()
        reg.register_prompt("test", version=1, template="v1")
        reg.register_prompt("test", version=3, template="v3")
        result = reg.get_prompt("test")
        assert result.version == 3
        assert result.template == "v3"


class TestGetLatestVersion:
    """Test latest version lookup."""

    def test_returns_none_for_unknown(self):
        reg = PromptRegistry()
        assert reg.get_latest_version("unknown") is None

    def test_returns_max_version(self):
        reg = PromptRegistry()
        reg.register_prompt("test", version=1, template="v1")
        reg.register_prompt("test", version=5, template="v5")
        reg.register_prompt("test", version=3, template="v3")
        assert reg.get_latest_version("test") == 5


class TestListPrompts:
    """Test listing all prompt entries."""

    def test_empty_registry(self):
        reg = PromptRegistry()
        # After reset, list may include builtins from _ensure_initialized
        # Just verify it returns a list
        result = reg.list_prompts()
        assert isinstance(result, list)

    def test_includes_registered_prompts(self):
        reg = PromptRegistry()
        reg.register_prompt("a", version=1, template="tmpl_a")
        reg.register_prompt("b", version=1, template="tmpl_b")
        names = {e.name for e in reg.list_prompts()}
        assert "a" in names
        assert "b" in names


class TestBuiltinPrompts:
    """Test that built-in prompts are loaded on first access."""

    def test_builtins_loaded(self):
        reg = PromptRegistry()
        prompts = reg.list_prompts()
        builtin_names = {e.name for e in prompts if e.metadata and e.metadata.get("source") == "builtin"}
        assert "architecture_system" in builtin_names
        assert "compliance_evaluation" in builtin_names
        assert "bicep_generation" in builtin_names
