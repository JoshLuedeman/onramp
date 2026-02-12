"""Tests for the prompt engineering framework."""

from app.services.prompts import (
    ARCHITECTURE_SYSTEM_PROMPT,
    COMPLIANCE_EVALUATION_PROMPT,
    BICEP_GENERATION_PROMPT,
    build_architecture_prompt,
)


def test_architecture_prompt_covers_caf_areas():
    prompt = ARCHITECTURE_SYSTEM_PROMPT
    assert "management group" in prompt.lower()
    assert "network" in prompt.lower()
    assert "identity" in prompt.lower()
    assert "security" in prompt.lower()
    assert "governance" in prompt.lower()
    assert "monitoring" in prompt.lower() or "management" in prompt.lower()
    assert "automation" in prompt.lower() or "devops" in prompt.lower()


def test_compliance_prompt_structure():
    assert "score" in COMPLIANCE_EVALUATION_PROMPT
    assert "gaps" in COMPLIANCE_EVALUATION_PROMPT
    assert "remediation" in COMPLIANCE_EVALUATION_PROMPT


def test_bicep_prompt_includes_best_practices():
    assert "modules" in BICEP_GENERATION_PROMPT.lower()
    assert "@secure()" in BICEP_GENERATION_PROMPT
    assert "parameters" in BICEP_GENERATION_PROMPT.lower()


def test_build_architecture_prompt():
    answers = {
        "org_name": "Contoso",
        "org_size": "medium",
        "industry": "healthcare",
        "compliance_frameworks": ["hipaa", "soc2"],
        "network_topology": "hub_spoke",
    }
    prompt = build_architecture_prompt(answers)
    assert "Contoso" in prompt
    assert "medium" in prompt
    assert "healthcare" in prompt
    assert "hipaa" in prompt
    assert "hub_spoke" in prompt
